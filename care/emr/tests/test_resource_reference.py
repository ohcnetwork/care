from unittest.mock import patch
from uuid import uuid4

from django.db import connection
from django.http import Http404
from django.test.utils import CaptureQueriesContext
from model_bakery import baker
from rest_framework.exceptions import PermissionDenied, ValidationError

from care.emr.models.condition import Condition
from care.emr.models.file_upload import FileUpload
from care.emr.models.questionnaire import Questionnaire
from care.emr.models.referral import (
    Referral,
    ReferralAvailability,
    ReferralQuestionnaireResponse,
)
from care.emr.models.scheduling.booking import TokenBooking, TokenSlot
from care.emr.models.scheduling.schedule import (
    Availability,
    SchedulableResource,
    Schedule,
)
from care.emr.utils.resource_reference import (
    ConditionResourceReferenceHandler,
    ResourceReferenceHandler,
    ResourceReferenceRegistry,
    get_resource_handler,
)
from care.security.permissions.encounter import EncounterPermissions
from care.security.permissions.service_request import ServiceRequestPermissions
from care.utils.tests.base import CareAPITestBase


class ResourceReferenceTests(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.patient = self.create_patient()
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )
        self.condition = baker.make(
            Condition,
            patient=self.patient,
            encounter=self.encounter,
            note="Original finding",
        )

    def test_resource_can_be_authorized_and_rendered_without_an_owning_referral(self):
        handler = get_resource_handler("condition")
        resource = handler.get_object(self.condition.external_id)
        with self.assertRaises(PermissionDenied):
            handler.authorize_read(self.user, resource)
        role = self.create_role_with_permissions(
            permissions=[EncounterPermissions.can_read_encounter_clinical_data.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        handler.authorize_read(self.user, resource)
        self.condition.note = "Updated finding"
        self.condition.save(update_fields=["note"])
        rendered = handler.render(handler.get_object(self.condition.external_id))
        self.assertEqual(rendered["id"], str(self.condition.external_id))
        self.assertEqual(rendered["note"], "Updated finding")
        self.assertFalse(Referral.objects.exists())

    def test_rendering_can_follow_an_owners_delegated_authorization(self):
        handler = get_resource_handler("condition")
        with self.assertRaises(PermissionDenied):
            handler.authorize_read(self.user, self.condition)

        rendered = handler.render(self.condition)
        self.assertEqual(rendered["id"], str(self.condition.external_id))
        self.assertEqual(rendered["note"], self.condition.note)

    def test_plugin_can_override_authorization_and_rendering_after_lookup(self):
        original_handler = get_resource_handler("condition")
        observation_handler = ResourceReferenceRegistry.get("observation")
        allowed_user_id = self.user.id

        class PluginConditionHandler(ConditionResourceReferenceHandler):
            def can_read(self, user, resource):
                return user.id == allowed_user_id

            def render(self, resource):
                return {"id": str(resource.external_id), "plugin": "custom assessment"}

        with patch.dict(ResourceReferenceRegistry._registry):  # noqa: SLF001
            registered = ResourceReferenceRegistry.register(PluginConditionHandler)
            self.assertIs(registered, PluginConditionHandler)
            handler = get_resource_handler("condition")
            self.assertIsInstance(handler, PluginConditionHandler)
            resource = handler.get_object(self.condition.external_id)
            handler.authorize_read(self.user, resource)
            with self.assertRaises(PermissionDenied):
                handler.authorize_read(self.create_user(), resource)
            self.assertEqual(
                handler.render(resource),
                {
                    "id": str(self.condition.external_id),
                    "plugin": "custom assessment",
                },
            )
            self.assertIs(
                ResourceReferenceRegistry.get("observation"), observation_handler
            )
            with self.assertRaises(PermissionDenied):
                original_handler.authorize_read(self.user, resource)

        self.assertIsInstance(
            get_resource_handler("condition"), ConditionResourceReferenceHandler
        )
        self.assertNotIsInstance(
            get_resource_handler("condition"), PluginConditionHandler
        )

    def test_plugin_can_register_a_new_resource_kind(self):
        allowed_user_id = self.user.id

        class PluginAssessmentHandler(ConditionResourceReferenceHandler):
            resource_type = "plugin_assessment"

            def can_read(self, user, resource):
                return user.id == allowed_user_id

        with patch.dict(ResourceReferenceRegistry._registry):  # noqa: SLF001
            ResourceReferenceRegistry.register(PluginAssessmentHandler)
            handler = get_resource_handler("plugin_assessment")
            resource = handler.get_object(self.condition.external_id)
            handler.authorize_read(self.user, resource)
            self.assertEqual(handler.render(resource)["note"], self.condition.note)
            self.assertIsInstance(
                get_resource_handler("condition"), ConditionResourceReferenceHandler
            )

        with self.assertRaises(ValidationError):
            get_resource_handler("plugin_assessment")

    def test_registry_rejects_invalid_handlers_and_incomplete_configuration(self):
        with patch.dict(ResourceReferenceRegistry._registry):  # noqa: SLF001
            for handler in (
                object,
                ConditionResourceReferenceHandler(),
                ResourceReferenceHandler,
            ):
                with self.subTest(handler=handler), self.assertRaises(TypeError):
                    ResourceReferenceRegistry.register(handler)

            for field, value in (
                ("resource_type", ""),
                ("model", None),
                ("read_spec", None),
            ):
                with self.subTest(field=field):
                    incomplete = type(
                        "IncompleteHandler",
                        (ConditionResourceReferenceHandler,),
                        {field: value},
                    )
                    with self.assertRaises(ValueError):
                        ResourceReferenceRegistry.register(incomplete)

    def test_encounter_files_follow_source_encounter_read_permission(self):
        upload = baker.make(
            FileUpload,
            file_type="encounter",
            associating_id=str(self.encounter.external_id),
            upload_completed=True,
        )
        handler = get_resource_handler("file_upload")
        resource = handler.get_object(upload.external_id)
        with self.assertRaises(PermissionDenied):
            handler.authorize_read(self.user, resource)

        role = self.create_role_with_permissions(
            permissions=[EncounterPermissions.can_read_encounter_clinical_data.name]
        )
        membership = self.attach_role_facility_organization_user(
            self.organization, self.user, role
        )
        handler.authorize_read(self.user, resource)
        membership.delete()
        with self.assertRaises(PermissionDenied):
            handler.authorize_read(self.user, resource)

    def test_service_request_files_require_service_request_read_permission(self):
        service_request = self.create_service_request(
            patient=self.patient, facility=self.facility, encounter=self.encounter
        )
        upload = baker.make(
            FileUpload,
            file_type="service_request",
            associating_id=str(service_request.external_id),
            upload_completed=True,
        )
        handler = get_resource_handler("file_upload")
        clinical_role = self.create_role_with_permissions(
            permissions=[EncounterPermissions.can_read_encounter_clinical_data.name]
        )
        self.attach_role_facility_organization_user(
            self.organization, self.user, clinical_role
        )
        with self.assertRaises(PermissionDenied):
            handler.authorize_read(self.user, upload)

        service_role = self.create_role_with_permissions(
            permissions=[ServiceRequestPermissions.can_read_service_request.name]
        )
        self.attach_role_facility_organization_user(
            self.organization, self.user, service_role
        )
        handler.authorize_read(self.user, upload)

    def test_unsupported_resources_are_rejected(self):
        for resource_type in (
            "unknown",
            "diagnosis",
            "medication_request",
            "medication_dispense",
        ):
            with (
                self.subTest(resource_type=resource_type),
                self.assertRaises(ValidationError),
            ):
                get_resource_handler(resource_type)

    def test_missing_and_deleted_resources_are_unavailable(self):
        handler = get_resource_handler("condition")
        with self.assertRaises(Http404):
            handler.get_object(uuid4())
        self.condition.delete()
        with self.assertRaises(Http404):
            handler.get_object(self.condition.external_id)

    def test_referral_rendering_does_not_expand_response_history(self):
        availability = ReferralAvailability.objects.create(
            entity_type="facility",
            facility=self.facility,
            name="Consultation",
            status="active",
            referral_type="consultation",
        )
        referral = Referral.objects.create(
            availability=availability,
            patient=self.patient,
            encounter=self.encounter,
            title="Clinical referral",
        )
        questionnaire = baker.make(
            Questionnaire, status="active", subject_type="encounter", questions=[]
        )
        ReferralQuestionnaireResponse.objects.create(
            referral=referral,
            questionnaire=questionnaire,
            questionnaire_snapshot={"private": "Full clinical assessment"},
        )

        handler = get_resource_handler("referral")
        with CaptureQueriesContext(connection) as queries:
            rendered = handler.render(handler.get_object(referral.external_id))
        self.assertEqual(rendered["id"], str(referral.external_id))
        for collection in ("questionnaire_responses", "resources", "notes", "messages"):
            self.assertNotIn(collection, rendered)
        self.assertNotIn("Full clinical assessment", str(rendered))
        self.assertFalse(
            any(
                '"emr_referralquestionnaireresponse"' in query["sql"]
                for query in queries
            )
        )

    def test_appointment_rendering_keeps_patient_and_encounter_unexpanded(self):
        resource = baker.make(
            SchedulableResource,
            facility=self.facility,
            resource_type="practitioner",
            user=self.user,
        )
        schedule = baker.make(Schedule, resource=resource)
        availability = baker.make(Availability, schedule=schedule)
        slot = baker.make(TokenSlot, resource=resource, availability=availability)
        appointment = TokenBooking.objects.create(
            token_slot=slot,
            patient=self.patient,
            status="booked",
            note="Follow-up visit",
            booked_by=self.user,
        )

        handler = get_resource_handler("appointment")
        rendered = handler.render(handler.get_object(appointment.external_id))
        self.assertEqual(rendered["id"], str(appointment.external_id))
        self.assertEqual(rendered["note"], appointment.note)
        for related in ("patient", "associated_encounter", "charge_item", "token"):
            self.assertNotIn(related, rendered)
