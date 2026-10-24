import uuid
from copy import deepcopy

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from model_bakery import baker

from care.emr.models.condition import Condition
from care.emr.models.notes import NoteMessage, NoteThread
from care.emr.models.observation import Observation
from care.emr.models.patient import PatientUser
from care.emr.models.questionnaire import Questionnaire, QuestionnaireResponse
from care.emr.models.referral import (
    Referral,
    ReferralAvailability,
    ReferralAvailabilityQuestionnaire,
    ReferralQuestionnaireResponse,
    ReferralResource,
)
from care.emr.models.scheduling.booking import TokenBooking, TokenSlot
from care.emr.models.scheduling.schedule import (
    Availability,
    SchedulableResource,
    Schedule,
)
from care.emr.resources.notes.constants import NoteThreadType
from care.emr.resources.referral.availability import (
    ReferralAvailabilityQuestionnaireSpec,
    ReferralAvailabilityReadSpec,
    ReferralAvailabilityRetrieveSpec,
)
from care.emr.resources.referral.spec import (
    ReferralQuestionnaireResponseCreateSpec,
    ReferralQuestionnaireResponseReadSpec,
    ReferralReadSpec,
    ReferralResourceCreateSpec,
    ReferralResourceReadSpec,
    ReferralResourceType,
    ReferralRetrieveSpec,
)
from care.security.permissions.encounter import EncounterPermissions
from care.security.permissions.patient import PatientPermissions
from care.security.permissions.questionnaire import QuestionnairePermissions
from care.security.permissions.referral import ReferralPermissions
from care.security.permissions.schedule import SchedulePermissions
from care.utils.tests.base import CareAPITestBase


class ReferralAPITestCase(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.destination_user = self.create_user()
        self.outsider = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.destination = self.create_facility(user=self.destination_user)
        self.destination_organization = self.create_facility_organization(
            facility=self.destination
        )
        self.patient = self.create_patient()
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )
        self.question_id = str(uuid.uuid4())
        self.questionnaire = baker.make(
            Questionnaire,
            title="Referral assessment",
            slug="referral-assessment",
            version="1.0",
            auth_context="facility",
            facility=self.destination,
            subject_type="encounter",
            status="active",
            internal_organization_cache=[self.destination_organization.id],
            questions=[
                {
                    "id": self.question_id,
                    "link_id": "reason",
                    "text": "Reason for referral",
                    "type": "text",
                    "required": True,
                }
            ],
        )
        self.availability = ReferralAvailability.objects.create(
            entity_type="facility",
            facility=self.destination,
            name="Specialist consultation",
            description="Consultation service",
            status="active",
            is_public=True,
            referral_type="consultation",
            created_by=self.destination_user,
            updated_by=self.destination_user,
        )
        self.availability.questionnaires.add(self.questionnaire)
        self.grant_origin(
            ReferralPermissions.can_create_referral.name,
            ReferralPermissions.can_read_referral.name,
            ReferralPermissions.can_write_referral.name,
            EncounterPermissions.can_read_encounter_clinical_data.name,
        )
        self.client.force_authenticate(user=self.user)

    def grant_origin(self, *permissions, user=None):
        role = self.create_role_with_permissions(permissions=list(permissions))
        return self.attach_role_facility_organization_user(
            self.organization, user or self.user, role
        )

    def grant_destination(self, *permissions, user=None, organization=None):
        role = self.create_role_with_permissions(permissions=list(permissions))
        if (
            organization is None
            and ReferralPermissions.can_manage_referral_availability.name in permissions
        ):
            self.attach_role_facility_organization_user(
                self.destination.default_internal_organization,
                user or self.destination_user,
                role,
            )
        return self.attach_role_facility_organization_user(
            organization or self.destination_organization,
            user or self.destination_user,
            role,
        )

    def grant_patient(self, *permissions, patient=None, user=None):
        role = self.create_role_with_permissions(permissions=list(permissions))
        return PatientUser.objects.create(
            patient=patient or self.patient, user=user or self.user, role=role
        )

    def availability_url(
        self, availability=None, action=None, *, entity_type="facility"
    ):
        name = "referral-availability-list"
        kwargs = {}
        if availability:
            name = f"referral-availability-{action or 'detail'}"
            kwargs["external_id"] = availability.external_id
        url = reverse(name, kwargs=kwargs)
        if availability is None and entity_type is not None:
            return f"{url}?entity_type={entity_type}"
        return url

    def availability_config_url(self, *, entity_type="facility", entity_id=None):
        entity_id = entity_id or self.destination.external_id
        return (
            f"{reverse('referral-availability-config-list')}?entity_type={entity_type}"
            f"&entity_id={entity_id}"
        )

    def referral_url(self, referral=None, action=None):
        name = "referral-list"
        kwargs = {}
        if referral:
            name = f"referral-{action or 'detail'}"
            kwargs["external_id"] = referral.external_id
        return reverse(name, kwargs=kwargs)

    def resource_url(self, referral, resource=None):
        name = "referral-resource-list"
        kwargs = {"referral_external_id": referral.external_id}
        if resource:
            name = "referral-resource-detail"
            kwargs["external_id"] = resource.external_id
        return reverse(name, kwargs=kwargs)

    def note_url(self, referral, note=None):
        name = "referral-note-list"
        kwargs = {"referral_external_id": referral.external_id}
        if note:
            name = "referral-note-detail"
            kwargs["external_id"] = note.external_id
        return reverse(name, kwargs=kwargs)

    def questionnaire_response_url(self, referral, questionnaire_response=None):
        name = "referral-questionnaire-response-list"
        kwargs = {"referral_external_id": referral.external_id}
        if questionnaire_response:
            name = "referral-questionnaire-response-detail"
            kwargs["external_id"] = questionnaire_response.external_id
        return reverse(name, kwargs=kwargs)

    def questionnaire_response_payload(self, **kwargs):
        payload = self.referral_payload()
        return {
            "questionnaire": payload["questionnaire"],
            "questionnaire_response": payload["questionnaire_response"],
            **kwargs,
        }

    def referral_payload(self, **kwargs):
        return {
            "title": "Specialist review requested",
            "note": "Please review the attached findings.",
            "availability": str(self.availability.external_id),
            "encounter": str(self.encounter.external_id),
            "questionnaire": str(self.questionnaire.external_id),
            "questionnaire_response": {
                "results": [
                    {
                        "question_id": self.question_id,
                        "values": [{"value": "Persistent symptoms"}],
                    }
                ]
            },
            **kwargs,
        }

    def create_referral(self, **kwargs):
        response = self.client.post(
            self.referral_url(), self.referral_payload(**kwargs), format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        return Referral.objects.get(external_id=response.data["id"])

    def patient_referral_payload(self, patient=None, **kwargs):
        self.questionnaire.subject_type = "patient"
        self.questionnaire.save(update_fields=["subject_type"])
        return self.referral_payload(
            patient=str((patient or self.patient).external_id),
            encounter=None,
            **kwargs,
        )

    def test_patient_referral_can_be_created_without_any_encounter(self):
        patient = self.create_patient()
        self.grant_patient(
            ReferralPermissions.can_create_referral.name,
            ReferralPermissions.can_read_referral.name,
            ReferralPermissions.can_write_referral.name,
            patient=patient,
        )
        for omit_encounter in (True, False):
            with self.subTest(omit_encounter=omit_encounter):
                payload = self.patient_referral_payload(patient=patient)
                if omit_encounter:
                    payload.pop("encounter")
                response = self.client.post(self.referral_url(), payload, format="json")
                self.assertEqual(response.status_code, 200, response.data)
                self.assertIsNone(response.data["encounter"])
                self.assertEqual(response.data["patient"], str(patient.external_id))
                self.assertEqual(response.data["patient_name"], patient.name)
                self.assertEqual(
                    response.data["availability_name"], self.availability.name
                )
                referral = Referral.objects.get(external_id=response.data["id"])
                self.assertEqual(referral.patient_id, patient.id)
                self.assertIsNone(referral.encounter_id)
                self.assertEqual(
                    referral.questionnaire_responses.get().questionnaire_response[
                        "cleaned_response"
                    ],
                    {"reason": "Persistent symptoms"},
                )
        self.assertFalse(patient.encounter_set.exists())
        self.assertFalse(QuestionnaireResponse.objects.exists())

    def test_encounter_referral_derives_patient_and_accepts_matching_patient(self):
        for fields in ({}, {"patient": str(self.patient.external_id)}):
            with self.subTest(fields=fields):
                referral = self.create_referral(**fields)
                self.assertEqual(referral.patient_id, self.patient.id)
                self.assertEqual(referral.encounter_id, self.encounter.id)

    def test_referral_rejects_a_patient_that_does_not_match_the_encounter(self):
        response = self.client.post(
            self.referral_url(),
            self.referral_payload(patient=str(self.create_patient().external_id)),
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Referral.objects.exists())

    def test_patient_referral_rejects_missing_or_invalid_origin(self):
        payload = self.patient_referral_payload()
        payload.pop("patient")
        for fields in ({}, {"patient": None}, {"patient": "invalid"}):
            with self.subTest(fields=fields):
                response = self.client.post(
                    self.referral_url(), {**payload, **fields}, format="json"
                )
                self.assertEqual(response.status_code, 400, response.data)
        missing = self.client.post(
            self.referral_url(),
            {**payload, "patient": str(uuid.uuid4())},
            format="json",
        )
        self.assertEqual(missing.status_code, 404, missing.data)
        self.assertFalse(Referral.objects.exists())

    def test_patient_referral_requires_patient_subject_form(self):
        response = self.client.post(
            self.referral_url(),
            self.referral_payload(
                patient=str(self.patient.external_id), encounter=None
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Referral.objects.exists())

    def test_patient_filter_includes_referrals_with_and_without_encounters(self):
        encounter_referral = self.create_referral()
        response = self.client.post(
            self.referral_url(), self.patient_referral_payload(), format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        patient_referral_id = response.data["id"]
        self.grant_destination(
            ReferralPermissions.can_read_referral.name,
            organization=self.destination.default_internal_organization,
        )
        self.client.force_authenticate(user=self.destination_user)
        response = self.client.get(
            self.referral_url(),
            {
                "entity_type": "facility",
                "entity_id": str(self.destination.external_id),
                "patient": str(self.patient.external_id),
            },
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertCountEqual(
            [row["id"] for row in response.data["results"]],
            [str(encounter_referral.external_id), patient_referral_id],
        )
        response = self.client.get(
            self.referral_url(),
            {
                "entity_type": "facility",
                "entity_id": str(self.destination.external_id),
                "encounter": str(self.encounter.external_id),
            },
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            [row["id"] for row in response.data["results"]],
            [str(encounter_referral.external_id)],
        )
        response = self.client.get(
            self.referral_url(),
            {
                "entity_type": "facility",
                "entity_id": str(self.destination.external_id),
                "patient": str(self.create_patient().external_id),
            },
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 0)

    def test_patient_referral_origin_is_immutable(self):
        response = self.client.post(
            self.referral_url(), self.patient_referral_payload(), format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        referral = Referral.objects.get(external_id=response.data["id"])
        response = self.client.patch(
            self.referral_url(referral),
            {
                "note": "Updated referral",
                "patient": str(self.create_patient().external_id),
                "encounter": str(self.encounter.external_id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        referral.refresh_from_db()
        self.assertEqual(referral.patient_id, self.patient.id)
        self.assertIsNone(referral.encounter_id)

    def test_patient_referral_can_attach_same_patients_encounter_data(self):
        response = self.client.post(
            self.referral_url(), self.patient_referral_payload(), format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        referral = Referral.objects.get(external_id=response.data["id"])
        condition = baker.make(
            Condition, patient=self.patient, encounter=self.encounter
        )
        response = self.client.post(
            self.resource_url(referral),
            {"resource_type": "condition", "resource_id": str(condition.external_id)},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        attachment = ReferralResource.objects.get(external_id=response.data["id"])
        response = self.client.get(
            reverse(
                "referral-resource-resolve",
                kwargs={
                    "referral_external_id": referral.external_id,
                    "external_id": attachment.external_id,
                },
            )
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["resource"]["id"], str(condition.external_id))
        response = self.client.get(self.resource_url(referral))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        other_condition = baker.make(
            Condition, patient=self.create_patient(), encounter=self.encounter
        )
        response = self.client.post(
            self.resource_url(referral),
            {
                "resource_type": "condition",
                "resource_id": str(other_condition.external_id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        for resource_type in ReferralResourceType:
            with self.subTest(resource_type=resource_type):
                response = self.client.post(
                    self.resource_url(referral),
                    {
                        "resource_type": resource_type.value,
                        "resource_id": str(uuid.uuid4()),
                    },
                    format="json",
                )
                self.assertEqual(response.status_code, 404, response.data)
        self.assertEqual(ReferralResource.objects.filter(referral=referral).count(), 1)
        referral.refresh_from_db()
        self.assertIsNone(referral.encounter_id)

    def test_patient_referral_discussion_uses_referral_scope(self):
        response = self.client.post(
            self.referral_url(), self.patient_referral_payload(), format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        referral = Referral.objects.get(external_id=response.data["id"])
        response = self.client.post(
            self.referral_url(referral, "thread"), {}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        referral.refresh_from_db()
        self.assertEqual(referral.thread.patient_id, self.patient.id)
        self.assertIsNone(referral.thread.encounter_id)
        self.assertEqual(referral.thread.thread_type, NoteThreadType.referral)
        self.grant_destination(
            ReferralPermissions.can_read_referral.name,
            ReferralPermissions.can_write_referral.name,
            organization=self.destination.default_internal_organization,
        )
        self.client.force_authenticate(user=self.destination_user)
        response = self.client.post(
            self.note_url(referral),
            {"message": "Patient referral reviewed"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.note_url(referral))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertContains(response, "Patient referral reviewed")
        self.grant_patient(
            PatientPermissions.can_view_clinical_data.name, user=self.outsider
        )
        self.client.force_authenticate(user=self.outsider)
        response = self.client.get(
            reverse(
                "thread-list", kwargs={"patient_external_id": self.patient.external_id}
            )
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 0)
        for url in (
            self.referral_url(referral),
            self.note_url(referral),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertIn(response.status_code, (403, 404), response.data)
        response = self.client.get(self.referral_url(referral, "thread"))
        self.assertEqual(response.status_code, 405, response.data)

    def test_public_availability_can_be_browsed_without_destination_membership(self):
        self.client.force_authenticate(user=self.outsider)
        response = self.client.get(self.availability_url())
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        response = self.client.get(self.availability_url(self.availability))
        self.assertEqual(response.status_code, 200, response.data)

    def test_availability_list_omits_questionnaires_without_loading_them(self):
        self.create_response_questionnaire()
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(self.availability_url())
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertNotIn("questionnaires", response.data["results"][0])
        for model in (ReferralAvailabilityQuestionnaire, Questionnaire):
            table = model._meta.db_table  # noqa: SLF001
            self.assertFalse(
                any(f'"{table}"' in query["sql"] for query in queries),
                f"Availability lists must not load {table}",
            )
        self.assertNotIn(
            "questionnaires",
            ReferralAvailabilityReadSpec.model_json_schema()["properties"],
        )
        self.assertIn(
            "questionnaires",
            ReferralAvailabilityRetrieveSpec.model_json_schema()["properties"],
        )

    def test_availability_retrieve_loads_all_form_metadata_together(self):
        response_form = self.create_response_questionnaire()
        deleted_form = baker.make(Questionnaire, deleted=True)
        self.availability.questionnaires.add(deleted_form)
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(self.availability_url(self.availability))
        self.assertEqual(response.status_code, 200, response.data)
        metadata = {item["id"]: item for item in response.data["questionnaires"]}
        self.assertCountEqual(
            metadata,
            [str(self.questionnaire.external_id), str(response_form.external_id)],
        )
        for questionnaire, questionnaire_type in (
            (self.questionnaire, "request"),
            (response_form, "response"),
        ):
            self.assertEqual(
                metadata[str(questionnaire.external_id)],
                {
                    "id": str(questionnaire.external_id),
                    "slug": questionnaire.slug,
                    "title": questionnaire.title,
                    "status": questionnaire.status,
                    "questionnaire_type": questionnaire_type,
                },
            )
        for model in (ReferralAvailabilityQuestionnaire, Questionnaire):
            table = model._meta.db_table  # noqa: SLF001
            self.assertEqual(
                sum(f'"{table}"' in query["sql"] for query in queries),
                1,
                f"Availability detail must load {table} once for all forms",
            )

    def test_availability_create_and_updates_include_current_form_metadata(self):
        response_form = self.create_response_questionnaire()
        self.grant_destination(
            ReferralPermissions.can_manage_referral_availability.name,
            QuestionnairePermissions.can_read_questionnaire.name,
        )
        self.client.force_authenticate(user=self.destination_user)
        request_mapping = {
            "questionnaire": str(self.questionnaire.external_id),
            "questionnaire_type": "request",
        }
        created = self.client.post(
            self.availability_url(entity_type=None),
            {
                "entity_type": "facility",
                "facility": str(self.destination.external_id),
                "name": "New consultation service",
                "status": "active",
                "referral_type": "consultation",
                "questionnaires": [request_mapping],
            },
            format="json",
        )
        self.assertEqual(created.status_code, 200, created.data)
        self.assertEqual(len(created.data["questionnaires"]), 1)
        self.assertEqual(
            created.data["questionnaires"][0]["id"],
            str(self.questionnaire.external_id),
        )
        availability = ReferralAvailability.objects.get(external_id=created.data["id"])
        for method in (self.client.put, self.client.patch):
            with self.subTest(method=method.__name__):
                updated = method(
                    self.availability_url(availability),
                    {
                        "questionnaires": [
                            request_mapping,
                            {
                                "questionnaire": str(response_form.external_id),
                                "questionnaire_type": "response",
                            },
                        ]
                    },
                    format="json",
                )
                self.assertEqual(updated.status_code, 200, updated.data)
                self.assertEqual(
                    {
                        item["id"]: item["questionnaire_type"]
                        for item in updated.data["questionnaires"]
                    },
                    {
                        str(self.questionnaire.external_id): "request",
                        str(response_form.external_id): "response",
                    },
                )

    def test_private_availability_is_hidden_from_unrelated_users(self):
        self.availability.is_public = False
        self.availability.save()
        response = self.client.get(self.availability_url())
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 0)
        response = self.client.get(self.availability_url(self.availability))
        self.assertIn(response.status_code, (403, 404), response.data)

    def test_availability_selection_requires_a_valid_entity_type_on_list(self):
        for params in ({}, {"entity_type": "invalid"}):
            with self.subTest(params=params):
                response = self.client.get(
                    reverse("referral-availability-list"), params
                )
                self.assertEqual(response.status_code, 400, response.data)

    def test_availability_selection_browses_all_destinations_of_one_entity_type(self):
        other = ReferralAvailability.objects.create(
            entity_type="facility",
            facility=self.facility,
            name="Another facility service",
            status="active",
            is_public=True,
            referral_type="consultation",
        )
        internal = ReferralAvailability.objects.create(
            entity_type="internal_organization",
            internal_organization=self.destination_organization,
            facility=self.destination,
            name="Department service",
            status="active",
            is_public=True,
            referral_type="consultation",
        )
        self.client.force_authenticate(user=self.outsider)
        response = self.client.get(self.availability_url())
        self.assertEqual(response.status_code, 200, response.data)
        self.assertCountEqual(
            [item["id"] for item in response.data["results"]],
            [str(self.availability.external_id), str(other.external_id)],
        )
        response = self.client.get(
            self.availability_url(entity_type="internal_organization")
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [str(internal.external_id)],
        )

    def test_availability_selection_hides_nonactive_configs_even_from_managers(self):
        self.grant_destination(
            ReferralPermissions.can_manage_referral_availability.name
        )
        superuser = self.create_super_user()
        for status in ("draft", "inactive"):
            self.availability.status = status
            self.availability.save(update_fields=["status"])
            for user in (self.outsider, self.destination_user, superuser):
                with self.subTest(status=status, user=user.external_id):
                    self.client.force_authenticate(user=user)
                    response = self.client.get(self.availability_url())
                    self.assertEqual(response.status_code, 200, response.data)
                    self.assertEqual(response.data["count"], 0)
                    filtered = self.client.get(
                        self.availability_url(),
                        {"entity_type": "facility", "status": status},
                    )
                    self.assertEqual(filtered.status_code, 200, filtered.data)
                    self.assertEqual(filtered.data["count"], 0)
                    for action in (None, "questionnaires"):
                        detail = self.client.get(
                            self.availability_url(self.availability, action)
                        )
                        expected = 404 if user == self.outsider else 200
                        self.assertEqual(detail.status_code, expected, detail.data)

    def test_availability_detail_and_forms_do_not_require_list_query_parameters(self):
        self.client.force_authenticate(user=self.outsider)
        for action in (None, "questionnaires"):
            for params in (
                {},
                {"entity_type": "invalid", "entity_id": "invalid"},
                {
                    "entity_type": "internal_organization",
                    "entity_id": str(self.organization.external_id),
                },
            ):
                with self.subTest(action=action, params=params):
                    response = self.client.get(
                        self.availability_url(self.availability, action), params
                    )
                    self.assertEqual(response.status_code, 200, response.data)
        self.availability.is_public = False
        self.availability.save(update_fields=["is_public"])
        for action in (None, "questionnaires"):
            denied = self.client.get(self.availability_url(self.availability, action))
            self.assertEqual(denied.status_code, 404, denied.data)

    def test_availability_config_requires_a_valid_entity_type_and_id(self):
        self.client.force_authenticate(user=self.create_super_user())
        for params in (
            {},
            {"entity_type": "facility"},
            {"entity_id": str(self.destination.external_id)},
            {"entity_type": "facility", "entity_id": "invalid"},
            {
                "entity_type": "invalid",
                "entity_id": str(self.destination.external_id),
            },
            {
                "entity_type": "external",
                "entity_id": str(self.destination.external_id),
            },
        ):
            with self.subTest(params=params):
                response = self.client.get(
                    reverse("referral-availability-config-list"), params
                )
                self.assertEqual(response.status_code, 400, response.data)
        response = self.client.get(self.availability_config_url(entity_id=uuid.uuid4()))
        self.assertEqual(response.status_code, 404, response.data)

    def test_availability_config_is_a_list_only_endpoint(self):
        self.client.force_authenticate(user=self.create_super_user())
        for method in (
            self.client.post,
            self.client.put,
            self.client.patch,
            self.client.delete,
        ):
            with self.subTest(method=method.__name__):
                response = method(
                    self.availability_config_url(), {"name": "Changed"}, format="json"
                )
                self.assertEqual(response.status_code, 405, response.data)
        for suffix in (
            f"{self.availability.external_id}/",
            f"{self.availability.external_id}/questionnaires/",
        ):
            response = self.client.get(
                f"{reverse('referral-availability-config-list')}{suffix}"
            )
            self.assertEqual(response.status_code, 404)

    def test_availability_config_requires_manage_permission_even_for_public_configs(
        self,
    ):
        for permission in (
            ReferralPermissions.can_read_referral_availability.name,
            ReferralPermissions.can_submit_referral_availability.name,
        ):
            self.grant_destination(
                permission,
                user=self.outsider,
                organization=self.destination.default_internal_organization,
            )
        self.client.force_authenticate(user=self.outsider)
        response = self.client.get(self.availability_config_url())
        self.assertEqual(response.status_code, 403, response.data)
        for method in (self.client.put, self.client.patch, self.client.delete):
            with self.subTest(method=method.__name__):
                response = method(
                    self.availability_url(self.availability),
                    {"description": "Unauthorized change"},
                    format="json",
                )
                self.assertEqual(response.status_code, 403, response.data)
        self.availability.refresh_from_db()
        self.assertEqual(self.availability.description, "Consultation service")
        self.assertFalse(self.availability.deleted)

    def test_availability_config_scope_does_not_expose_other_destinations(self):
        self.client.force_authenticate(user=self.create_super_user())
        other = ReferralAvailability.objects.create(
            entity_type="facility",
            facility=self.facility,
            name="Another facility service",
            status="draft",
            referral_type="consultation",
        )
        internal = ReferralAvailability.objects.create(
            entity_type="internal_organization",
            internal_organization=self.destination_organization,
            facility=self.destination,
            name="Department service",
            status="draft",
            referral_type="consultation",
        )
        response = self.client.get(self.availability_config_url())
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [str(self.availability.external_id)],
        )
        for entity_type, entity, expected in (
            ("facility", self.facility, other),
            ("internal_organization", self.destination_organization, internal),
        ):
            response = self.client.get(
                self.availability_config_url(
                    entity_type=entity_type, entity_id=entity.external_id
                )
            )
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(
                [item["id"] for item in response.data["results"]],
                [str(expected.external_id)],
            )
        filtered = self.client.get(
            reverse("referral-availability-config-list"),
            {
                "entity_type": "facility",
                "entity_id": str(self.destination.external_id),
                "facility": str(self.facility.external_id),
            },
        )
        self.assertEqual(filtered.status_code, 200, filtered.data)
        self.assertEqual(filtered.data["count"], 0)

    def test_availability_creation_authorizes_the_body_destination_without_list_scope(
        self,
    ):
        self.grant_destination(
            ReferralPermissions.can_manage_referral_availability.name
        )
        self.client.force_authenticate(user=self.destination_user)
        payload = {
            "entity_type": "facility",
            "facility": str(self.destination.external_id),
            "name": "Body scoped service",
            "status": "draft",
            "referral_type": "consultation",
        }
        for params in (
            "",
            f"?entity_type=internal_organization&entity_id={self.organization.external_id}",
        ):
            with self.subTest(params=params):
                response = self.client.post(
                    f"{reverse('referral-availability-list')}{params}",
                    payload,
                    format="json",
                )
                self.assertEqual(response.status_code, 200, response.data)
                self.assertEqual(
                    response.data["facility"], str(self.destination.external_id)
                )
        denied = self.client.post(
            self.availability_url(),
            {**payload, "facility": str(self.facility.external_id)},
            format="json",
        )
        self.assertEqual(denied.status_code, 403, denied.data)

    def test_availability_config_lists_drafts_and_inactive_while_original_routes_manage_them(
        self,
    ):
        self.grant_destination(
            ReferralPermissions.can_manage_referral_availability.name
        )
        self.client.force_authenticate(user=self.destination_user)
        for status in ("draft", "inactive"):
            with self.subTest(status=status):
                self.availability.status = status
                self.availability.save(update_fields=["status"])
                with CaptureQueriesContext(connection) as queries:
                    listed = self.client.get(self.availability_config_url())
                self.assertEqual(listed.status_code, 200, listed.data)
                self.assertEqual(listed.data["count"], 1)
                self.assertNotIn("questionnaires", listed.data["results"][0])
                for model in (ReferralAvailabilityQuestionnaire, Questionnaire):
                    table = model._meta.db_table  # noqa: SLF001
                    self.assertFalse(
                        any(f'"{table}"' in query["sql"] for query in queries)
                    )
                detail = self.client.get(self.availability_url(self.availability))
                self.assertEqual(detail.status_code, 200, detail.data)
                self.assertEqual(len(detail.data["questionnaires"]), 1)
                forms = self.client.get(
                    self.availability_url(self.availability, "questionnaires")
                )
                self.assertEqual(forms.status_code, 200, forms.data)
                self.assertContains(forms, self.question_id)
                for method in (self.client.patch, self.client.put):
                    updated = method(
                        self.availability_url(self.availability),
                        {"description": f"Instructions for {status}"},
                        format="json",
                    )
                    self.assertEqual(updated.status_code, 200, updated.data)
                    self.assertEqual(updated.data["status"], status)

    def test_availability_original_routes_can_create_activate_and_delete_a_draft(self):
        self.grant_destination(
            ReferralPermissions.can_manage_referral_availability.name
        )
        self.client.force_authenticate(user=self.destination_user)
        created = self.client.post(
            self.availability_url(entity_type=None),
            {
                "entity_type": "facility",
                "facility": str(self.destination.external_id),
                "name": "Draft service",
                "status": "draft",
                "is_public": True,
                "referral_type": "consultation",
            },
            format="json",
        )
        self.assertEqual(created.status_code, 200, created.data)
        availability = ReferralAvailability.objects.get(external_id=created.data["id"])
        detail = self.client.get(self.availability_url(availability))
        self.assertEqual(detail.status_code, 200, detail.data)
        listed = self.client.get(self.availability_url())
        self.assertNotIn(
            str(availability.external_id),
            [item["id"] for item in listed.data["results"]],
        )
        activated = self.client.patch(
            self.availability_url(availability), {"status": "active"}, format="json"
        )
        self.assertEqual(activated.status_code, 200, activated.data)
        visible = self.client.get(self.availability_url(availability))
        self.assertEqual(visible.status_code, 200, visible.data)
        deleted = self.client.delete(self.availability_url(availability))
        self.assertEqual(deleted.status_code, 204, deleted.data)
        availability.refresh_from_db()
        self.assertTrue(availability.deleted)

    def test_inactive_public_availability_cannot_receive_a_referral(self):
        for status in ("draft", "inactive"):
            with self.subTest(status=status):
                self.availability.status = status
                self.availability.save()
                response = self.client.post(
                    self.referral_url(), self.referral_payload(), format="json"
                )
                self.assertIn(response.status_code, (400, 403, 404), response.data)
        self.assertFalse(Referral.objects.exists())

    def test_create_availability_requires_permission_on_the_destination(self):
        payload = {
            "entity_type": "facility",
            "facility": str(self.destination.external_id),
            "name": "New service",
            "status": "active",
            "is_public": True,
            "referral_type": "consultation",
            "questionnaires": [str(self.questionnaire.external_id)],
            "care_team": [],
        }
        response = self.client.post(
            self.availability_url(entity_type=None), payload, format="json"
        )
        self.assertEqual(response.status_code, 403, response.data)
        self.grant_destination(
            ReferralPermissions.can_manage_referral_availability.name,
            QuestionnairePermissions.can_read_questionnaire.name,
        )
        self.client.force_authenticate(user=self.destination_user)
        response = self.client.post(
            self.availability_url(entity_type=None), payload, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["name"], payload["name"])

    def test_invalid_destination_combination_is_rejected(self):
        self.client.force_authenticate(user=self.create_super_user())
        response = self.client.post(
            self.availability_url(entity_type=None),
            {
                "entity_type": "facility",
                "facility": str(self.destination.external_id),
                "external_organization": str(self.create_organization().external_id),
                "name": "Invalid target",
                "status": "active",
                "referral_type": "consultation",
                "questionnaires": [str(self.questionnaire.external_id)],
                "care_team": [],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)

    def test_internal_organization_availability_automatically_sets_its_facility(self):
        self.client.force_authenticate(user=self.create_super_user())
        created_ids = []
        for facility_data in (
            {},
            {"facility": None},
            {"facility": str(self.destination.external_id)},
        ):
            with self.subTest(facility_data=facility_data):
                payload = {
                    "entity_type": "internal_organization",
                    "internal_organization": str(
                        self.destination_organization.external_id
                    ),
                    "name": "Internal service",
                    "status": "active",
                    "is_public": True,
                    "referral_type": "consultation",
                    **facility_data,
                }
                response = self.client.post(
                    self.availability_url(entity_type=None),
                    payload,
                    format="json",
                )
                self.assertEqual(response.status_code, 200, response.data)
                self.assertEqual(
                    response.data["facility"], str(self.destination.external_id)
                )
                self.assertEqual(
                    response.data["internal_organization"],
                    str(self.destination_organization.external_id),
                )
                availability = ReferralAvailability.objects.get(
                    external_id=response.data["id"]
                )
                self.assertEqual(
                    availability.facility_id,
                    self.destination.id,
                )
                created_ids.append(str(availability.external_id))
                filtered = self.client.get(
                    self.availability_url(),
                    {
                        "facility": str(self.destination.external_id),
                        "entity_type": "internal_organization",
                    },
                )
                self.assertEqual(filtered.status_code, 200, filtered.data)
                self.assertCountEqual(
                    [row["id"] for row in filtered.data["results"]],
                    created_ids,
                )

    def test_internal_organization_availability_rejects_a_different_facility(self):
        self.client.force_authenticate(user=self.create_super_user())
        response = self.client.post(
            self.availability_url(entity_type=None),
            {
                "entity_type": "internal_organization",
                "internal_organization": str(self.destination_organization.external_id),
                "facility": str(self.facility.external_id),
                "name": "Mismatched internal service",
                "status": "active",
                "referral_type": "consultation",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(
            ReferralAvailability.objects.filter(
                name="Mismatched internal service"
            ).exists()
        )

    def test_supplemental_facility_does_not_allow_other_mixed_destinations(self):
        self.client.force_authenticate(user=self.create_super_user())
        external = self.create_organization()
        invalid_targets = [
            {
                "entity_type": "facility",
                "facility": str(self.destination.external_id),
                "internal_organization": str(self.destination_organization.external_id),
            },
            {
                "entity_type": "external_organization",
                "external_organization": str(external.external_id),
                "facility": str(self.destination.external_id),
            },
            {
                "entity_type": "internal_organization",
                "internal_organization": str(self.destination_organization.external_id),
                "external_organization": str(external.external_id),
                "facility": str(self.destination.external_id),
            },
        ]
        for target in invalid_targets:
            with self.subTest(target=target):
                response = self.client.post(
                    self.availability_url(entity_type=None),
                    {
                        **target,
                        "name": "Invalid mixed service",
                        "status": "active",
                        "referral_type": "consultation",
                    },
                    format="json",
                )
                self.assertEqual(response.status_code, 400, response.data)

    def test_internal_organization_facility_cannot_be_updated(self):
        self.client.force_authenticate(user=self.create_super_user())
        for initial_facility in (None, self.destination):
            availability = ReferralAvailability.objects.create(
                entity_type="internal_organization",
                internal_organization=self.destination_organization,
                facility=initial_facility,
                name="Internal service",
                status="active",
                referral_type="consultation",
            )
            expected_facility = (
                str(initial_facility.external_id) if initial_facility else None
            )
            for method in (self.client.patch, self.client.put):
                for facility in (
                    str(self.destination.external_id),
                    str(self.facility.external_id),
                    None,
                ):
                    with self.subTest(
                        initial_facility=initial_facility,
                        method=method.__name__,
                        facility=facility,
                    ):
                        response = method(
                            self.availability_url(availability),
                            {"facility": facility, "name": "Renamed internal service"},
                            format="json",
                        )
                        self.assertEqual(response.status_code, 200, response.data)
                        self.assertEqual(response.data["facility"], expected_facility)
                        self.assertEqual(
                            response.data["name"], "Renamed internal service"
                        )
                        availability.refresh_from_db()
                        self.assertEqual(availability.facility, initial_facility)
                        self.assertEqual(
                            availability.internal_organization,
                            self.destination_organization,
                        )

        response = self.client.put(
            self.availability_url(self.availability),
            {"facility": str(self.destination.external_id), "name": "Renamed service"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["name"], "Renamed service")
        self.availability.refresh_from_db()
        self.assertEqual(self.availability.facility, self.destination)

    def test_internal_organization_facility_does_not_broaden_access(self):
        availability = ReferralAvailability.objects.create(
            entity_type="internal_organization",
            internal_organization=self.destination_organization,
            facility=self.destination,
            name="Private internal service",
            status="active",
            is_public=False,
            referral_type="consultation",
        )
        referral = Referral.objects.create(
            availability=availability,
            patient=self.patient,
            encounter=self.encounter,
            title="Private referral",
        )
        sibling = self.create_facility_organization(facility=self.destination)
        role = self.create_role_with_permissions(
            permissions=[
                ReferralPermissions.can_read_referral_availability.name,
                ReferralPermissions.can_manage_referral_availability.name,
                ReferralPermissions.can_submit_referral_availability.name,
                ReferralPermissions.can_read_referral.name,
                ReferralPermissions.can_write_referral.name,
            ]
        )
        self.attach_role_facility_organization_user(sibling, self.outsider, role)
        self.client.force_authenticate(user=self.outsider)
        response = self.client.get(
            self.availability_url(),
            {
                "facility": str(self.destination.external_id),
                "entity_type": "internal_organization",
            },
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 0)
        response = self.client.get(self.availability_url(availability))
        self.assertEqual(response.status_code, 404, response.data)
        response = self.client.patch(
            self.availability_url(availability),
            {"name": "Changed"},
            format="json",
        )
        self.assertIn(response.status_code, (403, 404), response.data)
        response = self.client.get(self.referral_url(referral))
        self.assertEqual(response.status_code, 403, response.data)

    def test_form_rendering_uses_availability_permissions(self):
        self.client.force_authenticate(user=self.outsider)
        response = self.client.get(
            self.availability_url(self.availability, "questionnaires")
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertContains(response, self.question_id)
        self.availability.is_public = False
        self.availability.save()
        response = self.client.get(
            self.availability_url(self.availability, "questionnaires")
        )
        self.assertIn(response.status_code, (403, 404), response.data)

    def test_referral_form_rendering_keeps_private_inactive_forms_available(self):
        referral = self.create_referral()
        self.availability.status = "inactive"
        self.availability.is_public = False
        self.availability.save(update_fields=["status", "is_public"])
        self.grant_destination(
            ReferralPermissions.can_read_referral.name,
            organization=self.destination.default_internal_organization,
        )

        for user in (self.user, self.destination_user):
            with self.subTest(user=user.external_id):
                self.client.force_authenticate(user=user)
                denied = self.client.get(
                    self.availability_url(self.availability, "questionnaires")
                )
                self.assertIn(denied.status_code, (403, 404), denied.data)

                response = self.client.get(
                    self.referral_url(referral, "questionnaires")
                )
                self.assertEqual(response.status_code, 200, response.data)
                self.assertEqual(response.data["count"], 1)
                self.assertEqual(
                    response.data["results"][0]["id"],
                    str(self.questionnaire.external_id),
                )
                self.assertEqual(
                    response.data["results"][0]["questions"][0]["id"],
                    self.question_id,
                )

    def test_referral_form_rendering_rejects_users_without_referral_access(self):
        referral = self.create_referral()
        self.client.force_authenticate(user=self.outsider)
        public_forms = self.client.get(
            self.availability_url(self.availability, "questionnaires")
        )
        self.assertEqual(public_forms.status_code, 200, public_forms.data)

        response = self.client.get(self.referral_url(referral, "questionnaires"))
        self.assertIn(response.status_code, (403, 404), response.data)

    def test_patient_referral_form_rendering_only_returns_active_current_patient_forms(
        self,
    ):
        response = self.client.post(
            self.referral_url(), self.patient_referral_payload(), format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        referral = Referral.objects.get(external_id=response.data["id"])
        encounter_form = baker.make(
            Questionnaire,
            status="active",
            subject_type="encounter",
            questions=self.questionnaire.questions,
        )
        inactive_form = baker.make(
            Questionnaire,
            status="inactive",
            subject_type="patient",
            questions=self.questionnaire.questions,
        )
        outdated_form = baker.make(
            Questionnaire,
            status="active",
            subject_type="patient",
            latest_revision=self.questionnaire,
            questions=self.questionnaire.questions,
        )
        self.availability.questionnaires.add(
            encounter_form, inactive_form, outdated_form
        )

        response = self.client.get(self.referral_url(referral, "questionnaires"))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            [form["id"] for form in response.data["results"]],
            [str(self.questionnaire.external_id)],
        )

    def test_public_submission_requires_origin_permission(self):
        self.client.force_authenticate(user=self.outsider)
        response = self.client.post(
            self.referral_url(), self.referral_payload(), format="json"
        )
        self.assertEqual(response.status_code, 403, response.data)
        self.assertFalse(Referral.objects.exists())

    def test_private_submission_requires_destination_permission(self):
        self.availability.is_public = False
        self.availability.save()
        response = self.client.post(
            self.referral_url(), self.referral_payload(), format="json"
        )
        self.assertIn(response.status_code, (403, 404), response.data)
        self.grant_destination(
            ReferralPermissions.can_submit_referral_availability.name,
            user=self.user,
            organization=self.destination.default_internal_organization,
        )
        self.create_referral()

    def test_unmapped_questionnaire_cannot_start_referral(self):
        other_questionnaire = baker.make(
            Questionnaire,
            title="Unmapped form",
            slug="unmapped-form",
            status="active",
            subject_type="encounter",
            questions=deepcopy(self.questionnaire.questions),
        )
        response = self.client.post(
            self.referral_url(),
            self.referral_payload(questionnaire=str(other_questionnaire.external_id)),
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Referral.objects.exists())

    def test_invalid_form_answers_are_rejected_atomically(self):
        invalid_answers = [
            [],
            [{"question_id": self.question_id, "values": []}],
            [{"question_id": "invalid", "values": [{"value": "Answer"}]}],
        ]
        for results in invalid_answers:
            with self.subTest(results=results):
                response = self.client.post(
                    self.referral_url(),
                    self.referral_payload(questionnaire_response={"results": results}),
                    format="json",
                )
                self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Referral.objects.exists())
        self.assertFalse(ReferralQuestionnaireResponse.objects.exists())

    def test_submission_does_not_create_clinical_resources(self):
        referral = self.create_referral()
        self.assertEqual(referral.status, "pending")
        self.assertEqual(
            referral.questionnaire_responses.get().questionnaire_response["results"][0][
                "values"
            ][0]["value"],
            "Persistent symptoms",
        )
        self.assertFalse(QuestionnaireResponse.objects.exists())
        self.assertFalse(Observation.objects.exists())

    def test_referrals_and_questionnaires_share_answer_processing(self):
        self.client.force_authenticate(user=self.create_super_user())
        self.questionnaire.facility = self.facility
        self.questionnaire.save()
        payload = self.referral_payload()
        original_questions = deepcopy(self.questionnaire.questions)
        response = self.client.post(
            reverse(
                "questionnaire-submit",
                kwargs={"external_id": self.questionnaire.external_id},
            ),
            {
                "resource_id": str(self.encounter.external_id),
                "patient": str(self.patient.external_id),
                "encounter": str(self.encounter.external_id),
                **payload["questionnaire_response"],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        referral = self.create_referral()
        self.assertEqual(
            referral.questionnaire_responses.get().questionnaire_response[
                "cleaned_response"
            ],
            response.data["cleaned_response"],
        )
        self.assertEqual(
            referral.questionnaire_responses.get().questionnaire_snapshot["questions"],
            original_questions,
        )
        # Referral answer processing shares the engine without a second clinical
        # submission into the origin encounter.
        self.assertEqual(QuestionnaireResponse.objects.count(), 1)

    def test_referrals_and_questionnaires_return_the_same_validation_errors(self):
        self.client.force_authenticate(user=self.create_super_user())
        self.questionnaire.facility = self.facility
        self.questionnaire.questions[0]["type"] = "integer"
        self.questionnaire.save()
        payload = self.referral_payload()
        normal = self.client.post(
            reverse(
                "questionnaire-submit",
                kwargs={"external_id": self.questionnaire.external_id},
            ),
            {
                "resource_id": str(self.encounter.external_id),
                "patient": str(self.patient.external_id),
                "encounter": str(self.encounter.external_id),
                **payload["questionnaire_response"],
            },
            format="json",
        )
        referral = self.client.post(self.referral_url(), payload, format="json")
        self.assertEqual(normal.status_code, 400, normal.data)
        self.assertEqual(referral.status_code, 400, referral.data)
        self.assertEqual(referral.data, normal.data)
        self.assertFalse(Referral.objects.exists())
        self.assertFalse(QuestionnaireResponse.objects.exists())

    def test_referral_preserves_the_submitted_questionnaire_revision(self):
        referral = self.create_referral()
        original_questions = deepcopy(self.questionnaire.questions)
        self.questionnaire.questions = [
            {**original_questions[0], "text": "Updated question"}
        ]
        self.questionnaire.internal_revision = 2
        self.questionnaire.save()
        response = self.client.get(self.referral_url(referral))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            response.data["questionnaire_responses"][0]["questionnaire_revision"], 1
        )
        self.assertEqual(
            response.data["questionnaire_responses"][0]["questionnaire_snapshot"][
                "questions"
            ],
            original_questions,
        )
        self.assertEqual(
            response.data["questionnaire_responses"][0]["questionnaire_response"][
                "cleaned_response"
            ],
            {"reason": "Persistent symptoms"},
        )

    def test_retired_questionnaire_cannot_start_referral(self):
        self.questionnaire.status = "retired"
        self.questionnaire.save()
        response = self.client.post(
            self.referral_url(), self.referral_payload(), format="json"
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Referral.objects.exists())

    def create_response_questionnaire(self):
        questionnaire = baker.make(
            Questionnaire,
            title="Referral response assessment",
            slug="referral-response-assessment",
            version="1.0",
            auth_context="facility",
            facility=self.destination,
            subject_type="encounter",
            status="active",
            internal_organization_cache=[self.destination_organization.id],
            questions=deepcopy(self.questionnaire.questions),
        )
        self.availability.questionnaires.add(questionnaire)
        self.availability.questionnaire_mappings.filter(
            questionnaire=questionnaire
        ).update(questionnaire_type="response")
        return questionnaire

    def test_availability_questionnaire_types_are_configured_rendered_and_filtered(
        self,
    ):
        referral = self.create_referral()
        response_form = self.create_response_questionnaire()
        self.grant_destination(
            ReferralPermissions.can_manage_referral_availability.name,
            QuestionnairePermissions.can_read_questionnaire.name,
        )
        self.client.force_authenticate(user=self.destination_user)
        response = self.client.patch(
            self.availability_url(self.availability),
            {
                "questionnaires": [
                    {
                        "questionnaire": str(self.questionnaire.external_id),
                        "questionnaire_type": "request",
                    },
                    {
                        "questionnaire": str(response_form.external_id),
                        "questionnaire_type": "response",
                    },
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        expected_types = {
            str(self.questionnaire.external_id): "request",
            str(response_form.external_id): "response",
        }
        self.assertEqual(
            {
                item["id"]: item["questionnaire_type"]
                for item in response.data["questionnaires"]
            },
            expected_types,
        )
        response = self.client.get(
            self.availability_url(self.availability, "questionnaires")
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            {
                item["id"]: item["questionnaire_type"]
                for item in response.data["results"]
            },
            expected_types,
        )
        filtered = self.client.get(
            self.availability_url(self.availability, "questionnaires"),
            {"entity_type": "facility", "questionnaire_type": "response"},
        )
        self.assertEqual(filtered.status_code, 200, filtered.data)
        self.assertEqual(
            [item["id"] for item in filtered.data["results"]],
            [str(response_form.external_id)],
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.referral_url(referral, "questionnaires"))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            {
                item["id"]: item["questionnaire_type"]
                for item in response.data["results"]
            },
            expected_types,
        )
        filtered = self.client.get(
            self.referral_url(referral, "questionnaires"),
            {"questionnaire_type": "request"},
        )
        self.assertEqual(filtered.status_code, 200, filtered.data)
        self.assertEqual(
            [item["id"] for item in filtered.data["results"]],
            [str(self.questionnaire.external_id)],
        )

        self.client.force_authenticate(user=self.destination_user)
        legacy = self.client.patch(
            self.availability_url(self.availability),
            {"questionnaires": [str(response_form.external_id)]},
            format="json",
        )
        self.assertEqual(legacy.status_code, 200, legacy.data)
        self.assertEqual(
            legacy.data["questionnaires"][0]["questionnaire_type"], "request"
        )
        self.assertEqual(len(legacy.data["questionnaires"]), 1)

    def test_response_only_questionnaire_cannot_start_a_referral(self):
        response_form = self.create_response_questionnaire()
        response = self.client.post(
            self.referral_url(),
            self.referral_payload(
                questionnaire=str(response_form.external_id),
                questionnaire_type="request",
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Referral.objects.exists())
        self.assertFalse(ReferralQuestionnaireResponse.objects.exists())

    def test_invalid_or_duplicate_availability_questionnaire_types_are_rejected(self):
        self.grant_destination(
            ReferralPermissions.can_manage_referral_availability.name,
            QuestionnairePermissions.can_read_questionnaire.name,
        )
        self.client.force_authenticate(user=self.destination_user)
        identifier = str(self.questionnaire.external_id)
        for mappings in (
            [{"questionnaire": identifier, "questionnaire_type": "origin"}],
            [{"questionnaire": identifier, "questionnaire_type": None}],
            [
                {"questionnaire": identifier, "questionnaire_type": "request"},
                {"questionnaire": identifier, "questionnaire_type": "response"},
            ],
        ):
            with self.subTest(mappings=mappings):
                response = self.client.patch(
                    self.availability_url(self.availability),
                    {"questionnaires": mappings},
                    format="json",
                )
                self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(self.availability.questionnaire_mappings.count(), 1)
        self.assertEqual(
            self.availability.questionnaire_mappings.get().questionnaire_type, "request"
        )

    def test_referral_questionnaire_responses_can_be_classified_and_filtered(self):
        referral = self.create_referral()
        initial = referral.questionnaire_responses.get()
        self.assertEqual(initial.questionnaire_type, "request")
        response_form = self.create_response_questionnaire()
        expected_types = {str(initial.external_id): "request"}
        for fields, expected_type in (
            ({}, "request"),
            ({"questionnaire": str(response_form.external_id)}, "response"),
        ):
            with self.subTest(fields=fields):
                response = self.client.post(
                    self.questionnaire_response_url(referral),
                    self.questionnaire_response_payload(**fields),
                    format="json",
                )
                self.assertEqual(response.status_code, 200, response.data)
                self.assertEqual(response.data["questionnaire_type"], expected_type)
                saved = ReferralQuestionnaireResponse.objects.get(
                    external_id=response.data["id"]
                )
                self.assertEqual(saved.questionnaire_type, expected_type)
                expected_types[response.data["id"]] = expected_type
                detail = self.client.get(
                    self.questionnaire_response_url(referral, saved)
                )
                self.assertEqual(detail.status_code, 200, detail.data)
                self.assertEqual(detail.data["questionnaire_type"], expected_type)

        self.availability.questionnaire_mappings.filter(
            questionnaire=response_form
        ).update(questionnaire_type="request")
        response = self.client.get(self.referral_url(referral))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            {
                item["id"]: item["questionnaire_type"]
                for item in response.data["questionnaire_responses"]
            },
            expected_types,
        )
        for questionnaire_type in ("request", "response"):
            with self.subTest(questionnaire_type=questionnaire_type):
                response = self.client.get(
                    self.questionnaire_response_url(referral),
                    {"questionnaire_type": questionnaire_type},
                )
                self.assertEqual(response.status_code, 200, response.data)
                self.assertCountEqual(
                    [item["id"] for item in response.data["results"]],
                    [
                        identifier
                        for identifier, value in expected_types.items()
                        if value == questionnaire_type
                    ],
                )

    def test_questionnaire_type_is_read_only_in_the_response_creation_schema(self):
        self.assertNotIn(
            "questionnaire_type", ReferralQuestionnaireResponseCreateSpec.model_fields
        )
        self.assertNotIn(
            "questionnaire_type",
            ReferralQuestionnaireResponseCreateSpec.model_json_schema()["properties"],
        )
        self.assertIn(
            "questionnaire_type", ReferralQuestionnaireResponseReadSpec.model_fields
        )
        self.assertIn(
            "questionnaire_type",
            ReferralQuestionnaireResponseReadSpec.model_json_schema()["properties"],
        )

    def test_referral_classifications_use_descriptive_field_names(self):
        for schema in (
            ReferralAvailabilityQuestionnaireSpec,
            ReferralQuestionnaireResponseCreateSpec,
            ReferralQuestionnaireResponseReadSpec,
            ReferralResourceCreateSpec,
            ReferralResourceReadSpec,
        ):
            with self.subTest(schema=schema.__name__):
                self.assertNotIn("type", schema.model_fields)
                self.assertNotIn("type", schema.model_json_schema()["properties"])
        for model in (
            ReferralAvailabilityQuestionnaire,
            ReferralQuestionnaireResponse,
            ReferralResource,
        ):
            with self.subTest(model=model.__name__):
                self.assertFalse(hasattr(model, "type"))
        self.assertIn("attachment_type", ReferralResourceCreateSpec.model_fields)
        self.assertIn("attachment_type", ReferralResourceReadSpec.model_fields)

    def test_payload_type_cannot_override_configured_questionnaire_type(self):
        referral = self.create_referral()
        response_form = self.create_response_questionnaire()
        for questionnaire, configured_type in (
            (self.questionnaire, "request"),
            (response_form, "response"),
        ):
            for supplied_type in (
                "request",
                "response",
                "origin",
                "metadata",
                "invalid",
                "",
                None,
            ):
                with self.subTest(
                    configured_type=configured_type, supplied_type=supplied_type
                ):
                    response = self.client.post(
                        self.questionnaire_response_url(referral),
                        self.questionnaire_response_payload(
                            questionnaire=str(questionnaire.external_id),
                            questionnaire_type=supplied_type,
                        ),
                        format="json",
                    )
                    self.assertEqual(response.status_code, 200, response.data)
                    self.assertEqual(
                        response.data["questionnaire_type"], configured_type
                    )
                    saved = ReferralQuestionnaireResponse.objects.get(
                        external_id=response.data["id"]
                    )
                    self.assertEqual(saved.questionnaire_type, configured_type)
        self.assertEqual(referral.questionnaire_responses.count(), 15)

    def test_errored_questionnaire_response_keeps_its_request_response_type(self):
        referral = self.create_referral()
        response_form = self.create_response_questionnaire()
        response = self.client.post(
            self.questionnaire_response_url(referral),
            self.questionnaire_response_payload(
                questionnaire=str(response_form.external_id)
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        submitted = ReferralQuestionnaireResponse.objects.get(
            external_id=response.data["id"]
        )
        original_answers = deepcopy(submitted.questionnaire_response)
        response = self.client.delete(
            self.questionnaire_response_url(referral, submitted)
        )
        self.assertEqual(response.status_code, 204, response.data)
        submitted.refresh_from_db()
        self.assertEqual(submitted.status, "entered_in_error")
        self.assertEqual(submitted.questionnaire_type, "response")
        self.assertEqual(submitted.questionnaire_response, original_answers)
        response = self.client.patch(
            self.questionnaire_response_url(referral, submitted),
            {"questionnaire_type": "request"},
            format="json",
        )
        self.assertEqual(response.status_code, 405, response.data)
        response = self.client.get(
            self.questionnaire_response_url(referral),
            {"questionnaire_type": "response", "status": "entered_in_error"},
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [str(submitted.external_id)],
        )
        initial = referral.questionnaire_responses.exclude(id=submitted.id).get()
        self.assertEqual(initial.questionnaire_type, "request")
        self.assertEqual(initial.status, "completed")

    def test_referral_supports_multiple_independent_questionnaire_responses(self):
        referral = self.create_referral()
        initial = referral.questionnaire_responses.get()
        response = self.client.post(
            self.questionnaire_response_url(referral),
            self.questionnaire_response_payload(
                questionnaire_response={
                    "results": [
                        {
                            "question_id": self.question_id,
                            "values": [{"value": "Follow-up assessment"}],
                        }
                    ]
                },
                status="entered_in_error",
                questionnaire_revision=99,
                questionnaire_snapshot={"invalid": True},
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        additional = ReferralQuestionnaireResponse.objects.get(
            external_id=response.data["id"]
        )
        self.assertEqual(additional.status, "completed")
        self.assertEqual(additional.referral_id, referral.id)
        self.assertEqual(additional.questionnaire_id, self.questionnaire.id)
        self.assertEqual(additional.questionnaire_revision, 1)
        self.assertEqual(
            additional.questionnaire_snapshot["questions"], self.questionnaire.questions
        )
        self.assertEqual(
            additional.questionnaire_response["cleaned_response"],
            {"reason": "Follow-up assessment"},
        )
        initial.refresh_from_db()
        self.assertEqual(
            initial.questionnaire_response["cleaned_response"],
            {"reason": "Persistent symptoms"},
        )
        response = self.client.get(self.questionnaire_response_url(referral))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertCountEqual(
            [item["id"] for item in response.data["results"]],
            [str(initial.external_id), str(additional.external_id)],
        )
        response = self.client.get(self.referral_url(referral))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data["questionnaire_responses"]), 2)
        for singular in (
            "questionnaire",
            "questionnaire_response",
            "questionnaire_revision",
            "questionnaire_snapshot",
        ):
            self.assertNotIn(singular, response.data)
        self.assertFalse(QuestionnaireResponse.objects.exists())
        self.assertFalse(Observation.objects.exists())

    def test_referral_list_omits_questionnaire_responses_without_loading_them(self):
        referral = self.create_referral()
        self.assertEqual(referral.questionnaire_responses.count(), 1)
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(
                self.referral_url(), {"encounter": str(self.encounter.external_id)}
            )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertNotIn("questionnaire_responses", response.data["results"][0])
        for table in ("emr_referralquestionnaireresponse", "emr_questionnaire"):
            self.assertFalse(
                any(f'"{table}"' in query["sql"] for query in queries),
                f"Referral lists must not load {table}",
            )
        self.assertNotIn(
            "questionnaire_responses",
            ReferralReadSpec.model_json_schema()["properties"],
        )
        self.assertIn(
            "questionnaire_responses",
            ReferralRetrieveSpec.model_json_schema()["properties"],
        )

    def test_referral_retrieve_and_mutations_include_response_history(self):
        created = self.client.post(
            self.referral_url(), self.referral_payload(), format="json"
        )
        self.assertEqual(created.status_code, 200, created.data)
        self.assertEqual(len(created.data["questionnaire_responses"]), 1)
        referral = Referral.objects.get(external_id=created.data["id"])
        initial = referral.questionnaire_responses.get()
        additional = self.client.post(
            self.questionnaire_response_url(referral),
            self.questionnaire_response_payload(),
            format="json",
        )
        self.assertEqual(additional.status_code, 200, additional.data)
        errored = self.client.delete(self.questionnaire_response_url(referral, initial))
        self.assertEqual(errored.status_code, 204, errored.data)

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(self.referral_url(referral))
        self.assertEqual(response.status_code, 200, response.data)
        history = {
            item["id"]: item for item in response.data["questionnaire_responses"]
        }
        self.assertCountEqual(
            history, [str(initial.external_id), additional.data["id"]]
        )
        self.assertEqual(
            history[str(initial.external_id)]["status"], "entered_in_error"
        )
        self.assertEqual(history[additional.data["id"]]["status"], "completed")
        for item in history.values():
            self.assertEqual(item["questionnaire_type"], "request")
            self.assertEqual(item["questionnaire_revision"], 1)
            self.assertEqual(
                item["questionnaire_snapshot"]["questions"],
                self.questionnaire.questions,
            )
        for table in ("emr_referralquestionnaireresponse", "emr_questionnaire"):
            self.assertEqual(
                sum(f'"{table}"' in query["sql"] for query in queries),
                1,
                f"Referral detail must load {table} once for all responses",
            )

        updated = self.client.patch(
            self.referral_url(referral), {"note": "Follow-up note"}, format="json"
        )
        self.assertEqual(updated.status_code, 200, updated.data)
        self.assertEqual(len(updated.data["questionnaire_responses"]), 2)

    def test_existing_responses_keep_their_own_questionnaire_revision(self):
        referral = self.create_referral()
        initial = referral.questionnaire_responses.get()
        initial_snapshot = deepcopy(initial.questionnaire_snapshot)
        self.questionnaire.internal_revision = 2
        self.questionnaire.questions[0]["text"] = "Revised assessment question"
        self.questionnaire.save()
        response = self.client.post(
            self.questionnaire_response_url(referral),
            self.questionnaire_response_payload(),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["questionnaire_revision"], 2)
        self.assertEqual(
            response.data["questionnaire_snapshot"]["questions"],
            self.questionnaire.questions,
        )
        initial.refresh_from_db()
        self.assertEqual(initial.questionnaire_revision, 1)
        self.assertEqual(initial.questionnaire_snapshot, initial_snapshot)

    def test_questionnaire_response_error_status_preserves_answers_and_other_responses(
        self,
    ):
        referral = self.create_referral()
        initial = referral.questionnaire_responses.get()
        original = {
            field: deepcopy(getattr(initial, field))
            for field in (
                "questionnaire_response",
                "questionnaire_revision",
                "questionnaire_snapshot",
                "questionnaire_type",
                "questionnaire_id",
                "referral_id",
                "created_by_id",
                "created_date",
                "history",
                "deleted",
            )
        }
        response = self.client.post(
            self.questionnaire_response_url(referral),
            self.questionnaire_response_payload(),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        additional = ReferralQuestionnaireResponse.objects.get(
            external_id=response.data["id"]
        )
        self.availability.questionnaires.remove(self.questionnaire)
        self.questionnaire.status = "retired"
        self.questionnaire.save(update_fields=["status"])
        self.grant_destination(
            ReferralPermissions.can_read_referral.name,
            ReferralPermissions.can_write_referral.name,
            organization=self.destination.default_internal_organization,
        )
        self.client.force_authenticate(user=self.destination_user)
        response = self.client.delete(
            self.questionnaire_response_url(referral, initial)
        )
        self.assertEqual(response.status_code, 204, response.data)
        initial.refresh_from_db()
        self.assertEqual(initial.status, "entered_in_error")
        self.assertFalse(initial.deleted)
        self.assertEqual(initial.updated_by_id, self.destination_user.id)
        for field, value in original.items():
            self.assertEqual(getattr(initial, field), value)
        additional.refresh_from_db()
        self.assertEqual(additional.status, "completed")
        response = self.client.get(self.questionnaire_response_url(referral))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 2)
        response = self.client.get(self.questionnaire_response_url(referral, initial))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["status"], "entered_in_error")
        self.assertEqual(
            response.data["questionnaire_response"], original["questionnaire_response"]
        )
        self.assertEqual(
            self.client.delete(
                self.questionnaire_response_url(referral, initial)
            ).status_code,
            204,
        )
        for method in (self.client.put, self.client.patch):
            response = method(
                self.questionnaire_response_url(referral, initial),
                {"status": "completed"},
                format="json",
            )
            self.assertEqual(response.status_code, 405, response.data)
        initial.refresh_from_db()
        self.assertEqual(initial.status, "entered_in_error")
        for field, value in original.items():
            self.assertEqual(getattr(initial, field), value)

    def test_response_routes_use_referral_permissions_and_bind_the_parent(self):
        referral = self.create_referral()
        response = referral.questionnaire_responses.get()
        another = self.create_referral()
        wrong_parent = self.client.get(
            self.questionnaire_response_url(another, response)
        )
        self.assertEqual(wrong_parent.status_code, 404, wrong_parent.data)
        wrong_parent = self.client.delete(
            self.questionnaire_response_url(another, response)
        )
        self.assertEqual(wrong_parent.status_code, 404, wrong_parent.data)
        self.grant_destination(
            ReferralPermissions.can_read_referral.name,
            organization=self.destination.default_internal_organization,
        )
        self.client.force_authenticate(user=self.destination_user)
        readable = self.client.get(self.questionnaire_response_url(referral))
        self.assertEqual(readable.status_code, 200, readable.data)
        self.assertEqual(readable.data["count"], 1)
        readable = self.client.get(self.questionnaire_response_url(referral, response))
        self.assertEqual(readable.status_code, 200, readable.data)
        denied = self.client.post(
            self.questionnaire_response_url(referral),
            self.questionnaire_response_payload(),
            format="json",
        )
        self.assertEqual(denied.status_code, 403, denied.data)
        denied = self.client.delete(self.questionnaire_response_url(referral, response))
        self.assertEqual(denied.status_code, 403, denied.data)
        self.client.force_authenticate(user=self.outsider)
        for url in (
            self.questionnaire_response_url(referral),
            self.questionnaire_response_url(referral, response),
        ):
            denied = self.client.get(url)
            self.assertIn(denied.status_code, (403, 404), denied.data)
        denied = self.client.delete(self.questionnaire_response_url(referral, response))
        self.assertIn(denied.status_code, (403, 404), denied.data)
        denied = self.client.post(
            self.questionnaire_response_url(referral),
            self.questionnaire_response_payload(),
            format="json",
        )
        self.assertEqual(denied.status_code, 403, denied.data)
        response.refresh_from_db()
        self.assertEqual(response.status, "completed")
        self.assertEqual(referral.questionnaire_responses.count(), 1)

    def test_destination_writer_can_submit_mapped_form_without_questionnaire_access(
        self,
    ):
        referral = self.create_referral()
        another = self.create_referral()
        self.availability.status = "inactive"
        self.availability.is_public = False
        self.availability.save(update_fields=["status", "is_public"])
        self.grant_destination(
            ReferralPermissions.can_write_referral.name,
            organization=self.destination.default_internal_organization,
        )
        self.client.force_authenticate(user=self.destination_user)
        denied = self.client.get(
            reverse(
                "questionnaire-detail",
                kwargs={"external_id": self.questionnaire.external_id},
            )
        )
        self.assertIn(denied.status_code, (403, 404), denied.data)
        response = self.client.post(
            self.questionnaire_response_url(referral),
            self.questionnaire_response_payload(),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(referral.questionnaire_responses.count(), 2)
        created = ReferralQuestionnaireResponse.objects.get(
            external_id=response.data["id"]
        )
        self.assertEqual(created.created_by_id, self.destination_user.id)
        wrong_parent = self.client.delete(
            self.questionnaire_response_url(another, created)
        )
        self.assertEqual(wrong_parent.status_code, 404, wrong_parent.data)
        created.refresh_from_db()
        self.assertEqual(created.status, "completed")
        deleted = self.client.delete(self.questionnaire_response_url(referral, created))
        self.assertEqual(deleted.status_code, 204, deleted.data)
        created.refresh_from_db()
        self.assertEqual(created.status, "entered_in_error")
        self.assertFalse(created.deleted)
        self.assertEqual(created.updated_by_id, self.destination_user.id)
        self.assertEqual(referral.questionnaire_responses.count(), 2)
        self.assertEqual(
            referral.questionnaire_responses.exclude(id=created.id).get().status,
            "completed",
        )

    def test_existing_referral_can_submit_responses_after_availability_is_deleted(self):
        referral = self.create_referral()
        self.grant_destination(
            ReferralPermissions.can_manage_referral_availability.name
        )
        self.client.force_authenticate(user=self.destination_user)
        deleted = self.client.delete(self.availability_url(self.availability))
        self.assertEqual(deleted.status_code, 204, deleted.data)
        self.availability.refresh_from_db()
        self.assertTrue(self.availability.deleted)

        self.client.force_authenticate(user=self.user)
        new_referral = self.client.post(
            self.referral_url(), self.referral_payload(), format="json"
        )
        self.assertEqual(new_referral.status_code, 404, new_referral.data)
        detail = self.client.get(self.referral_url(referral))
        self.assertEqual(detail.status_code, 200, detail.data)
        self.assertEqual(detail.data["status"], "pending")
        forms = self.client.get(self.referral_url(referral, "questionnaires"))
        self.assertEqual(forms.status_code, 200, forms.data)
        self.assertEqual(forms.data["count"], 1)
        self.assertEqual(
            forms.data["results"][0]["id"], str(self.questionnaire.external_id)
        )
        response = self.client.post(
            self.questionnaire_response_url(referral),
            self.questionnaire_response_payload(),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(referral.questionnaire_responses.count(), 2)
        self.assertEqual(Referral.objects.count(), 1)

    def test_invalid_additional_responses_do_not_change_existing_submissions(self):
        referral = self.create_referral()
        initial = referral.questionnaire_responses.get()
        original_answers = deepcopy(initial.questionnaire_response)
        other = baker.make(
            Questionnaire,
            status="active",
            subject_type="encounter",
            questions=self.questionnaire.questions,
        )
        unmapped = self.client.post(
            self.questionnaire_response_url(referral),
            self.questionnaire_response_payload(questionnaire=str(other.external_id)),
            format="json",
        )
        self.assertEqual(unmapped.status_code, 400, unmapped.data)
        for results in ([], [{"question_id": self.question_id, "values": []}]):
            invalid = self.client.post(
                self.questionnaire_response_url(referral),
                self.questionnaire_response_payload(
                    questionnaire_response={"results": results}
                ),
                format="json",
            )
            self.assertEqual(invalid.status_code, 400, invalid.data)
        self.questionnaire.status = "retired"
        self.questionnaire.save(update_fields=["status"])
        inactive = self.client.post(
            self.questionnaire_response_url(referral),
            self.questionnaire_response_payload(),
            format="json",
        )
        self.assertEqual(inactive.status_code, 400, inactive.data)
        self.questionnaire.status = "active"
        self.questionnaire.latest_revision = other
        self.questionnaire.save(update_fields=["status", "latest_revision"])
        outdated = self.client.post(
            self.questionnaire_response_url(referral),
            self.questionnaire_response_payload(),
            format="json",
        )
        self.assertEqual(outdated.status_code, 400, outdated.data)
        self.assertEqual(referral.questionnaire_responses.count(), 1)
        initial.refresh_from_db()
        self.assertEqual(initial.questionnaire_response, original_answers)
        self.assertFalse(QuestionnaireResponse.objects.exists())

    def test_patient_referral_additional_responses_require_patient_subject_forms(self):
        response = self.client.post(
            self.referral_url(), self.patient_referral_payload(), format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        referral = Referral.objects.get(external_id=response.data["id"])
        additional = self.client.post(
            self.questionnaire_response_url(referral),
            self.questionnaire_response_payload(),
            format="json",
        )
        self.assertEqual(additional.status_code, 200, additional.data)
        encounter_form = baker.make(
            Questionnaire,
            status="active",
            subject_type="encounter",
            questions=self.questionnaire.questions,
        )
        self.availability.questionnaires.add(encounter_form)
        invalid = self.client.post(
            self.questionnaire_response_url(referral),
            self.questionnaire_response_payload(
                questionnaire=str(encounter_form.external_id)
            ),
            format="json",
        )
        self.assertEqual(invalid.status_code, 400, invalid.data)
        self.assertEqual(referral.questionnaire_responses.count(), 2)

    def test_resource_types_can_be_classified_and_filtered(self):
        referral = self.create_referral()
        attachments = {}
        for category in ("source", "response", "metadata"):
            condition = baker.make(
                Condition, patient=self.patient, encounter=self.encounter
            )
            response = self.client.post(
                self.resource_url(referral),
                {
                    "resource_type": "condition",
                    "resource_id": str(condition.external_id),
                    "attachment_type": category,
                    "metadata": {"label": category},
                },
                format="json",
            )
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data["attachment_type"], category)
            attachment = ReferralResource.objects.get(external_id=response.data["id"])
            self.assertEqual(attachment.attachment_type, category)
            attachments[category] = attachment
        for category, attachment in attachments.items():
            response = self.client.get(
                self.resource_url(referral),
                {"attachment_type": category, "resource_type": "condition"},
            )
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(
                [item["id"] for item in response.data["results"]],
                [str(attachment.external_id)],
            )
        source = attachments["source"]
        duplicate = self.client.post(
            self.resource_url(referral),
            {
                "attachment_type": "metadata",
                "resource_type": source.resource_type,
                "resource_id": str(source.resource_id),
            },
            format="json",
        )
        self.assertEqual(duplicate.status_code, 400, duplicate.data)

    def test_attachment_type_defaults_to_source_and_invalid_types_are_rejected(self):
        referral = self.create_referral()
        condition = baker.make(
            Condition, patient=self.patient, encounter=self.encounter
        )
        body = {"resource_type": "condition", "resource_id": str(condition.external_id)}
        for invalid in ("clinical", "", None):
            response = self.client.post(
                self.resource_url(referral),
                {**body, "attachment_type": invalid},
                format="json",
            )
            self.assertEqual(response.status_code, 400, response.data)
        response = self.client.post(self.resource_url(referral), body, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["attachment_type"], "source")
        attachment = ReferralResource.objects.get(external_id=response.data["id"])
        response = self.client.patch(
            self.resource_url(referral, attachment),
            {"attachment_type": "invalid"},
            format="json",
        )
        self.assertEqual(response.status_code, 405, response.data)
        attachment.refresh_from_db()
        self.assertEqual(attachment.attachment_type, "source")

    def test_destination_reader_can_access_without_origin_encounter_permission(self):
        referral = self.create_referral()
        self.grant_destination(
            ReferralPermissions.can_read_referral.name,
            organization=self.destination.default_internal_organization,
        )
        self.client.force_authenticate(user=self.destination_user)
        response = self.client.get(self.referral_url(referral))
        self.assertEqual(response.status_code, 200, response.data)
        response = self.client.get(
            self.referral_url(),
            {"entity_type": "facility", "entity_id": str(self.destination.external_id)},
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)

    def test_referral_responses_show_names_and_enforce_read_write_access(self):
        response = self.client.post(
            self.referral_url(), self.referral_payload(), format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["patient_name"], self.patient.name)
        self.assertEqual(response.data["availability_name"], self.availability.name)
        referral = Referral.objects.get(external_id=response.data["id"])
        response = self.client.patch(
            self.referral_url(referral), {"status": "in_progress"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["status"], "in_progress")

        self.grant_destination(
            ReferralPermissions.can_read_referral.name,
            organization=self.destination.default_internal_organization,
        )
        self.client.force_authenticate(user=self.destination_user)
        response = self.client.get(self.referral_url(referral))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["patient_name"], self.patient.name)
        self.assertEqual(response.data["availability_name"], self.availability.name)
        response = self.client.get(
            self.referral_url(),
            {"entity_type": "facility", "entity_id": str(self.destination.external_id)},
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["patient_name"], self.patient.name)
        self.assertEqual(
            response.data["results"][0]["availability_name"], self.availability.name
        )
        denied = self.client.patch(
            self.referral_url(referral), {"status": "completed"}, format="json"
        )
        self.assertEqual(denied.status_code, 403, denied.data)
        referral.refresh_from_db()
        self.assertEqual(referral.status, "in_progress")

    def test_public_availability_read_access_does_not_grant_management(self):
        self.client.force_authenticate(user=self.outsider)
        for url in (
            self.availability_url(self.availability),
            self.availability_url(),
        ):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, response.data)
        response = self.client.patch(
            self.availability_url(self.availability),
            {"description": "Unauthorized update"},
            format="json",
        )
        self.assertEqual(response.status_code, 403, response.data)
        response = self.client.delete(self.availability_url(self.availability))
        self.assertEqual(response.status_code, 403, response.data)
        self.availability.refresh_from_db()
        self.assertEqual(self.availability.description, "Consultation service")
        self.assertFalse(self.availability.deleted)

    def test_public_availability_does_not_expose_referrals(self):
        referral = self.create_referral()
        self.client.force_authenticate(user=self.outsider)
        response = self.client.get(
            self.referral_url(),
            {"entity_type": "facility", "entity_id": str(self.destination.external_id)},
        )
        self.assertEqual(response.status_code, 403, response.data)
        response = self.client.get(self.referral_url(referral))
        self.assertIn(response.status_code, (403, 404), response.data)
        response = self.client.patch(
            self.referral_url(referral), {"status": "completed"}, format="json"
        )
        self.assertIn(response.status_code, (403, 404), response.data)

    def test_read_permission_does_not_allow_updates(self):
        referral = self.create_referral()
        self.grant_destination(ReferralPermissions.can_read_referral.name)
        self.client.force_authenticate(user=self.destination_user)
        response = self.client.patch(
            self.referral_url(referral), {"status": "in_progress"}, format="json"
        )
        self.assertEqual(response.status_code, 403, response.data)
        referral.refresh_from_db()
        self.assertEqual(referral.status, "pending")

    def test_facility_filter_includes_internal_organization_destinations(self):
        direct_referral = self.create_referral()
        self.client.force_authenticate(user=self.create_super_user())
        created = self.client.post(
            self.availability_url(entity_type=None),
            {
                "entity_type": "internal_organization",
                "internal_organization": str(self.destination_organization.external_id),
                "name": "Department consultation",
                "status": "active",
                "is_public": True,
                "referral_type": "consultation",
            },
            format="json",
        )
        self.assertEqual(created.status_code, 200, created.data)
        availability = ReferralAvailability.objects.get(external_id=created.data["id"])
        availability.questionnaires.add(self.questionnaire)
        self.assertEqual(availability.facility_id, self.destination.id)
        self.client.force_authenticate(user=self.user)
        department_referral = self.create_referral(
            availability=str(availability.external_id)
        )

        response = self.client.get(
            self.referral_url(),
            {
                "encounter": str(self.encounter.external_id),
                "facility": str(self.destination.external_id),
            },
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertCountEqual(
            [row["id"] for row in response.data["results"]],
            [str(direct_referral.external_id), str(department_referral.external_id)],
        )

        response = self.client.get(
            self.referral_url(),
            {
                "encounter": str(self.encounter.external_id),
                "facility": str(self.facility.external_id),
            },
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 0)

        self.client.force_authenticate(user=self.outsider)
        response = self.client.get(
            self.referral_url(),
            {
                "encounter": str(self.encounter.external_id),
                "facility": str(self.destination.external_id),
            },
        )
        self.assertEqual(response.status_code, 403, response.data)

    def test_auto_assignment_and_pending_filters(self):
        self.availability.care_team = [
            {
                "user_id": self.user.id,
                "role": {"system": "http://snomed.info/sct", "code": "doctor"},
            }
        ]
        self.availability.save()
        referral = self.create_referral()
        self.assertEqual(referral.assignee_users, [self.user.id])
        self.assertEqual(referral.assignees, self.availability.care_team)
        response = self.client.get(
            self.referral_url(),
            {
                "encounter": str(self.encounter.external_id),
                "assigned_to_me": "true",
                "pending": "true",
            },
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        response = self.client.patch(
            self.referral_url(referral), {"status": "completed"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        response = self.client.get(
            self.referral_url(),
            {
                "encounter": str(self.encounter.external_id),
                "assigned_to_me": "true",
                "pending": "true",
            },
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 0)

    def test_updating_assignees_refreshes_cache_and_does_not_grant_access(self):
        referral = self.create_referral()
        response = self.client.patch(
            self.referral_url(referral),
            {
                "assignees": [
                    {
                        "user_id": str(self.outsider.external_id),
                        "role": {
                            "system": "http://snomed.info/sct",
                            "code": "doctor",
                        },
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        referral.refresh_from_db()
        self.assertEqual(referral.assignee_users, [self.outsider.id])
        self.client.force_authenticate(user=self.outsider)
        response = self.client.get(
            self.referral_url(),
            {
                "encounter": str(self.encounter.external_id),
                "assigned_to_me": "true",
                "pending": "true",
            },
        )
        self.assertEqual(response.status_code, 403, response.data)

    def test_attach_resource_stores_reference_and_metadata(self):
        referral = self.create_referral()
        condition = baker.make(
            Condition, patient=self.patient, encounter=self.encounter
        )
        metadata = {"label": "Presenting diagnosis"}
        response = self.client.post(
            self.resource_url(referral),
            {
                "resource_type": "condition",
                "resource_id": str(condition.external_id),
                "metadata": metadata,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        resource = ReferralResource.objects.get(external_id=response.data["id"])
        self.assertEqual(resource.resource_id, condition.external_id)
        self.assertEqual(resource.metadata, metadata)
        response = self.client.get(self.resource_url(referral))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)

    def test_unsupported_resource_types_cannot_be_attached(self):
        referral = self.create_referral()
        for resource_type in ("diagnosis", "medication_request", "medication_dispense"):
            with self.subTest(resource_type=resource_type):
                response = self.client.post(
                    self.resource_url(referral),
                    {
                        "resource_type": resource_type,
                        "resource_id": str(uuid.uuid4()),
                    },
                    format="json",
                )
                self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(ReferralResource.objects.exists())

    def test_destination_writer_can_manage_resources_without_referral_read_access(self):
        referral = self.create_referral()
        other_referral = self.create_referral(title="Other referral")
        condition = baker.make(
            Condition, patient=self.patient, encounter=self.encounter
        )
        payload = {
            "resource_type": "condition",
            "resource_id": str(condition.external_id),
        }
        self.grant_destination(
            ReferralPermissions.can_write_referral.name,
            organization=self.destination.default_internal_organization,
        )
        self.client.force_authenticate(user=self.destination_user)
        denied = self.client.post(self.resource_url(referral), payload, format="json")
        self.assertEqual(denied.status_code, 403, denied.data)
        self.assertFalse(ReferralResource.objects.exists())

        source_access = self.grant_origin(
            EncounterPermissions.can_read_encounter_clinical_data.name,
            user=self.destination_user,
        )
        created = self.client.post(self.resource_url(referral), payload, format="json")
        self.assertEqual(created.status_code, 200, created.data)
        attachment = ReferralResource.objects.get(external_id=created.data["id"])
        for url in (
            self.resource_url(referral),
            self.resource_url(referral, attachment),
            reverse(
                "referral-resource-resolve",
                kwargs={
                    "referral_external_id": referral.external_id,
                    "external_id": attachment.external_id,
                },
            ),
        ):
            denied = self.client.get(url)
            self.assertEqual(denied.status_code, 403, denied.data)

        source_access.delete()
        for method, attachment_type in (
            (self.client.put, "response"),
            (self.client.patch, "metadata"),
        ):
            with self.subTest(method=method.__name__):
                update = {
                    "attachment_type": attachment_type,
                    "metadata": {"label": attachment_type},
                }
                wrong_parent = method(
                    self.resource_url(other_referral, attachment), update, format="json"
                )
                self.assertEqual(wrong_parent.status_code, 405, wrong_parent.data)
                updated = method(
                    self.resource_url(referral, attachment), update, format="json"
                )
                self.assertEqual(updated.status_code, 405, updated.data)
                attachment.refresh_from_db()
                self.assertEqual(attachment.attachment_type, "source")
                self.assertEqual(attachment.metadata, {})
                self.assertEqual(attachment.resource_id, condition.external_id)

        wrong_parent = self.client.delete(self.resource_url(other_referral, attachment))
        self.assertEqual(wrong_parent.status_code, 404, wrong_parent.data)
        deleted = self.client.delete(self.resource_url(referral, attachment))
        self.assertEqual(deleted.status_code, 204, deleted.data)
        self.assertFalse(ReferralResource.objects.filter(id=attachment.id).exists())
        self.assertTrue(Condition.objects.filter(id=condition.id).exists())

    def test_resource_validation_rejects_wrong_patient_and_missing_resource(self):
        referral = self.create_referral()
        other_condition = baker.make(
            Condition, patient=self.create_patient(), encounter=self.encounter
        )
        for resource_id in (other_condition.external_id, uuid.uuid4()):
            with self.subTest(resource_id=resource_id):
                response = self.client.post(
                    self.resource_url(referral),
                    {"resource_type": "condition", "resource_id": str(resource_id)},
                    format="json",
                )
                self.assertIn(response.status_code, (400, 404), response.data)
        self.assertFalse(ReferralResource.objects.exists())

    def test_another_encounters_resource_requires_source_access(self):
        referral = self.create_referral()
        other_encounter = self.create_encounter(
            patient=self.patient,
            facility=self.destination,
            organization=self.destination_organization,
        )
        condition = baker.make(
            Condition, patient=self.patient, encounter=other_encounter
        )
        payload = {
            "resource_type": "condition",
            "resource_id": str(condition.external_id),
        }
        response = self.client.post(self.resource_url(referral), payload, format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.assertFalse(ReferralResource.objects.exists())
        self.grant_destination(
            EncounterPermissions.can_read_encounter_clinical_data.name, user=self.user
        )
        response = self.client.post(self.resource_url(referral), payload, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        attachment = ReferralResource.objects.get(external_id=response.data["id"])
        self.grant_destination(
            ReferralPermissions.can_read_referral.name,
            organization=self.destination.default_internal_organization,
        )
        self.client.force_authenticate(user=self.destination_user)
        response = self.client.get(
            reverse(
                "referral-resource-resolve",
                kwargs={
                    "referral_external_id": referral.external_id,
                    "external_id": attachment.external_id,
                },
            )
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["resource"]["id"], str(condition.external_id))

    def create_appointment(self, patient=None):
        resource, _ = SchedulableResource.objects.get_or_create(
            facility=self.facility, resource_type="practitioner", user=self.user
        )
        schedule = baker.make(Schedule, resource=resource)
        availability = baker.make(Availability, schedule=schedule)
        slot = baker.make(TokenSlot, resource=resource, availability=availability)
        return TokenBooking.objects.create(
            token_slot=slot,
            patient=patient or self.patient,
            status="booked",
            note="Follow-up appointment",
            booked_by=self.user,
        )

    def test_appointment_attachment_uses_booking_access_and_minimal_live_resolution(
        self,
    ):
        referral = self.create_referral()
        appointment = self.create_appointment()
        payload = {
            "resource_type": "appointment",
            "resource_id": str(appointment.external_id),
            "metadata": {"label": "Follow-up visit"},
        }
        denied = self.client.post(self.resource_url(referral), payload, format="json")
        self.assertEqual(denied.status_code, 403, denied.data)
        self.assertFalse(ReferralResource.objects.exists())
        self.grant_origin(SchedulePermissions.can_list_booking.name)
        response = self.client.post(self.resource_url(referral), payload, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        attachment = ReferralResource.objects.get(external_id=response.data["id"])
        self.assertEqual(attachment.resource_id, appointment.external_id)
        self.assertEqual(attachment.metadata, payload["metadata"])
        duplicate = self.client.post(
            self.resource_url(referral), payload, format="json"
        )
        self.assertEqual(duplicate.status_code, 400, duplicate.data)

        appointment.note = "Updated appointment note"
        appointment.save(update_fields=["note"])
        self.grant_destination(
            ReferralPermissions.can_read_referral.name,
            organization=self.destination.default_internal_organization,
        )
        self.client.force_authenticate(user=self.destination_user)
        resolve_url = reverse(
            "referral-resource-resolve",
            kwargs={
                "referral_external_id": referral.external_id,
                "external_id": attachment.external_id,
            },
        )
        response = self.client.get(resolve_url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["resource_type"], "appointment")
        self.assertEqual(response.data["resource"]["id"], str(appointment.external_id))
        self.assertEqual(response.data["resource"]["status"], "booked")
        self.assertEqual(response.data["resource"]["note"], appointment.note)
        for expanded in ("patient", "associated_encounter", "charge_item", "token"):
            self.assertNotIn(expanded, response.data["resource"])
        appointment.delete()
        response = self.client.get(resolve_url)
        self.assertEqual(response.status_code, 404, response.data)

    def test_appointment_for_another_patient_cannot_be_attached(self):
        referral = self.create_referral()
        self.grant_origin(SchedulePermissions.can_list_booking.name)
        appointment = self.create_appointment(patient=self.create_patient())
        response = self.client.post(
            self.resource_url(referral),
            {
                "resource_type": "appointment",
                "resource_id": str(appointment.external_id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(ReferralResource.objects.exists())

    def test_patient_referral_can_attach_appointments_and_other_referrals(self):
        response = self.client.post(
            self.referral_url(), self.patient_referral_payload(), format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        referral = Referral.objects.get(external_id=response.data["id"])
        appointment = self.create_appointment()
        source_referral = self.create_referral()
        self.grant_origin(SchedulePermissions.can_list_booking.name)
        for resource_type, source in (
            ("appointment", appointment),
            ("referral", source_referral),
        ):
            with self.subTest(resource_type=resource_type):
                response = self.client.post(
                    self.resource_url(referral),
                    {
                        "resource_type": resource_type,
                        "resource_id": str(source.external_id),
                    },
                    format="json",
                )
                self.assertEqual(response.status_code, 200, response.data)
                response = self.client.get(
                    reverse(
                        "referral-resource-resolve",
                        kwargs={
                            "referral_external_id": referral.external_id,
                            "external_id": response.data["id"],
                        },
                    )
                )
                self.assertEqual(response.status_code, 200, response.data)
                self.assertEqual(
                    response.data["resource"]["id"], str(source.external_id)
                )
        referral.refresh_from_db()
        self.assertIsNone(referral.encounter_id)
        self.assertEqual(ReferralResource.objects.filter(referral=referral).count(), 2)

    def test_linked_referral_requires_source_access_without_expanding_its_resources(
        self,
    ):
        referral = self.create_referral()
        source_facility = self.create_facility(user=self.outsider)
        source_organization = self.create_facility_organization(
            facility=source_facility
        )
        source_encounter = self.create_encounter(
            patient=self.patient,
            facility=source_facility,
            organization=source_organization,
        )
        source_availability = ReferralAvailability.objects.create(
            entity_type="external",
            external_entity={"name": "Other referral destination"},
            name="Other referral service",
            status="active",
            is_public=True,
            referral_type="consultation",
            created_by=self.outsider,
        )
        source = Referral.objects.create(
            availability=source_availability,
            patient=self.patient,
            encounter=source_encounter,
            title="Earlier referral",
            note="Previous referral assessment",
        )
        source.thread = NoteThread.objects.create(
            patient=self.patient,
            encounter=source_encounter,
            thread_type=NoteThreadType.referral.value,
            title="Private source discussion",
        )
        source.save(update_fields=["thread"])
        NoteMessage.objects.create(thread=source.thread, message="Private source note")
        # A reference cycle must stay a pair of IDs rather than expand recursively.
        ReferralResource.objects.create(
            referral=source, resource_type="referral", resource_id=referral.external_id
        )
        payload = {"resource_type": "referral", "resource_id": str(source.external_id)}
        response = self.client.post(self.resource_url(referral), payload, format="json")
        self.assertEqual(response.status_code, 403, response.data)
        role = self.create_role_with_permissions(
            permissions=[ReferralPermissions.can_read_referral.name]
        )
        self.attach_role_facility_organization_user(
            source_organization, self.user, role
        )
        response = self.client.post(self.resource_url(referral), payload, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        attachment = ReferralResource.objects.get(external_id=response.data["id"])
        self.assertEqual(attachment.resource_id, source.external_id)
        duplicate = self.client.post(
            self.resource_url(referral), payload, format="json"
        )
        self.assertEqual(duplicate.status_code, 400, duplicate.data)

        self.grant_destination(
            ReferralPermissions.can_read_referral.name,
            organization=self.destination.default_internal_organization,
        )
        self.client.force_authenticate(user=self.destination_user)
        self.assertEqual(self.client.get(self.referral_url(source)).status_code, 403)
        resolve_url = reverse(
            "referral-resource-resolve",
            kwargs={
                "referral_external_id": referral.external_id,
                "external_id": attachment.external_id,
            },
        )
        source.note = "Updated source referral note"
        source.save(update_fields=["note"])
        response = self.client.get(resolve_url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["resource_type"], "referral")
        self.assertEqual(response.data["resource"]["id"], str(source.external_id))
        self.assertEqual(response.data["resource"]["note"], source.note)
        self.assertNotIn("permissions", response.data["resource"])
        for expanded in ("resources", "notes", "messages", "questionnaire_responses"):
            self.assertNotIn(expanded, response.data["resource"])
        self.assertNotIn("Private source note", str(response.data))
        self.assertIn(self.client.get(self.note_url(source)).status_code, (403, 404))
        source.delete()
        response = self.client.get(resolve_url)
        self.assertEqual(response.status_code, 404, response.data)

    def test_reverse_referral_lookup_returns_only_active_incoming_links(self):
        target = self.create_referral()
        referring = []
        for category in ("source", "response", "metadata"):
            parent = self.create_referral(title=f"Referring {category}")
            attachment = ReferralResource.objects.create(
                referral=parent,
                resource_type="referral",
                resource_id=target.external_id,
                attachment_type=category,
            )
            referring.append((parent, attachment))
        # A historical detached duplicate must not duplicate the referring record.
        ReferralResource.objects.create(
            referral=referring[0][0],
            resource_type="referral",
            resource_id=target.external_id,
            deleted=True,
        )
        unrelated = self.create_referral(title="Unrelated referral")
        ReferralResource.objects.create(
            referral=target,
            resource_type="referral",
            resource_id=unrelated.external_id,
        )
        # Invalid historical self-links must not include the current referral.
        ReferralResource.objects.create(
            referral=target,
            resource_type="referral",
            resource_id=target.external_id,
        )
        wrong_type = self.create_referral(title="Different resource kind")
        ReferralResource.objects.create(
            referral=wrong_type,
            resource_type="condition",
            resource_id=target.external_id,
        )
        removed = self.create_referral(title="Detached referral")
        ReferralResource.objects.create(
            referral=removed,
            resource_type="referral",
            resource_id=target.external_id,
            deleted=True,
        )
        deleted = self.create_referral(title="Deleted referring referral")
        ReferralResource.objects.create(
            referral=deleted,
            resource_type="referral",
            resource_id=target.external_id,
        )
        deleted.delete()
        other_patient = self.create_patient()
        other_encounter = self.create_encounter(
            patient=other_patient,
            facility=self.facility,
            organization=self.organization,
        )
        wrong_patient = Referral.objects.create(
            availability=self.availability,
            patient=other_patient,
            encounter=other_encounter,
            title="Invalid historical cross-patient link",
        )
        ReferralResource.objects.create(
            referral=wrong_patient,
            resource_type="referral",
            resource_id=target.external_id,
        )

        url = self.referral_url(target, "referenced-by")
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 3)
        self.assertCountEqual(
            [item["id"] for item in response.data["results"]],
            [str(parent.external_id) for parent, _ in referring],
        )
        self.assertNotIn("questionnaire_responses", response.data["results"][0])
        for table in ("emr_referralquestionnaireresponse", "emr_questionnaire"):
            self.assertFalse(
                any(f'"{table}"' in query["sql"] for query in queries),
                f"Reverse referral lists must not load {table}",
            )
        parent, attachment = referring[0]
        removed = self.client.delete(self.resource_url(parent, attachment))
        self.assertEqual(removed.status_code, 204, removed.data)
        response = self.client.get(url)
        self.assertEqual(response.data["count"], 2)
        reattached = self.client.post(
            self.resource_url(parent),
            {"resource_type": "referral", "resource_id": str(target.external_id)},
            format="json",
        )
        self.assertEqual(reattached.status_code, 200, reattached.data)
        response = self.client.get(url)
        self.assertEqual(response.data["count"], 3)

    def create_referral_in_other_scope(self):
        facility = self.create_facility(user=self.outsider)
        organization = self.create_facility_organization(facility=facility)
        encounter = self.create_encounter(
            patient=self.patient, facility=facility, organization=organization
        )
        availability = ReferralAvailability.objects.create(
            entity_type="external",
            external_entity={"name": "Restricted destination"},
            name="Restricted referral service",
            status="active",
            is_public=True,
            referral_type="consultation",
            created_by=self.outsider,
        )
        referral = Referral.objects.create(
            availability=availability,
            patient=self.patient,
            encounter=encounter,
            title="Restricted referral",
        )
        return referral, organization

    def test_reverse_referral_lookup_returns_metadata_without_parent_read_permission(
        self,
    ):
        target = self.create_referral()
        url = self.referral_url(target, "referenced-by")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data, {"count": 0, "results": []})
        parent, organization = self.create_referral_in_other_scope()
        ReferralResource.objects.create(
            referral=parent,
            resource_type="referral",
            resource_id=target.external_id,
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(parent.external_id))
        self.assertNotIn("questionnaire_responses", response.data["results"][0])
        denied = self.client.get(self.referral_url(parent))
        self.assertEqual(denied.status_code, 403, denied.data)

        role = self.create_role_with_permissions(
            permissions=[ReferralPermissions.can_read_referral.name]
        )
        membership = self.attach_role_facility_organization_user(
            organization, self.user, role
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(parent.external_id))
        allowed = self.client.get(self.referral_url(parent))
        self.assertEqual(allowed.status_code, 200, allowed.data)
        membership.delete()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(parent.external_id))
        denied = self.client.get(self.referral_url(parent))
        self.assertEqual(denied.status_code, 403, denied.data)

    def test_reverse_referral_returns_all_matching_parents_without_pagination(self):
        target = self.create_referral()
        first = self.create_referral(title="First parent")
        restricted, _ = self.create_referral_in_other_scope()
        second = self.create_referral(title="Second parent")
        for parent in (first, restricted, second):
            ReferralResource.objects.create(
                referral=parent,
                resource_type="referral",
                resource_id=target.external_id,
            )

        url = self.referral_url(target, "referenced-by")
        expected = [
            str(first.external_id),
            str(restricted.external_id),
            str(second.external_id),
        ]
        for pagination_params in (
            {},
            {"limit": 1, "offset": 0},
            {"limit": 1, "offset": 1},
            {"limit": 1, "offset": 100},
        ):
            with self.subTest(pagination_params=pagination_params):
                response = self.client.get(
                    url, {"ordering": "created_date", **pagination_params}
                )
                self.assertEqual(response.status_code, 200, response.data)
                self.assertEqual(set(response.data), {"count", "results"})
                self.assertEqual(response.data["count"], 3)
                self.assertEqual(
                    [item["id"] for item in response.data["results"]], expected
                )

    def test_reverse_referral_lookup_requires_access_to_the_target(self):
        target, _ = self.create_referral_in_other_scope()
        parent = self.create_referral()
        ReferralResource.objects.create(
            referral=parent,
            resource_type="referral",
            resource_id=target.external_id,
        )
        response = self.client.get(self.referral_url(target, "referenced-by"))
        self.assertEqual(response.status_code, 403, response.data)
        self.client.force_authenticate(user=self.create_super_user())
        response = self.client.get(self.referral_url(target, "referenced-by"))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(parent.external_id))
        missing = self.client.get(
            reverse("referral-referenced-by", kwargs={"external_id": uuid.uuid4()})
        )
        self.assertEqual(missing.status_code, 404, missing.data)
        target.delete()
        deleted = self.client.get(self.referral_url(target, "referenced-by"))
        self.assertEqual(deleted.status_code, 404, deleted.data)
        self.client.force_authenticate(user=None)
        denied = self.client.get(self.referral_url(target, "referenced-by"))
        self.assertIn(denied.status_code, (401, 403), denied.data)

    def test_reverse_referral_filters_and_ordering_apply_only_to_results(self):
        target = self.create_referral()
        completed = []
        for title in ("First completed referral", "Second completed referral"):
            parent = self.create_referral(title=title)
            parent.status = "completed"
            parent.save(update_fields=["status"])
            ReferralResource.objects.create(
                referral=parent,
                resource_type="referral",
                resource_id=target.external_id,
            )
            completed.append(parent)
        pending = self.create_referral(title="Pending referring referral")
        ReferralResource.objects.create(
            referral=pending,
            resource_type="referral",
            resource_id=target.external_id,
        )
        url = self.referral_url(target, "referenced-by")
        response = self.client.get(
            url,
            {
                "status": "completed",
                "ordering": "created_date",
                "limit": 1,
                "offset": 1,
            },
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [str(parent.external_id) for parent in completed],
        )
        response = self.client.get(
            url, {"status": "completed", "ordering": "-created_date", "limit": 1}
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [str(parent.external_id) for parent in reversed(completed)],
        )

    def test_referral_cannot_reference_itself_or_another_patients_referral(self):
        referral = self.create_referral()
        other_patient = self.create_patient()
        other_encounter = self.create_encounter(
            patient=other_patient,
            facility=self.facility,
            organization=self.organization,
        )
        other_referral = Referral.objects.create(
            availability=self.availability,
            patient=other_patient,
            encounter=other_encounter,
            title="Another patient's referral",
        )
        for source in (referral, other_referral):
            with self.subTest(source=source.external_id):
                response = self.client.post(
                    self.resource_url(referral),
                    {
                        "resource_type": "referral",
                        "resource_id": str(source.external_id),
                    },
                    format="json",
                )
                self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(ReferralResource.objects.exists())

    def test_duplicate_resource_attachment_is_rejected(self):
        referral = self.create_referral()
        condition = baker.make(
            Condition, patient=self.patient, encounter=self.encounter
        )
        payload = {
            "resource_type": "condition",
            "resource_id": str(condition.external_id),
        }
        response = self.client.post(self.resource_url(referral), payload, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        response = self.client.post(self.resource_url(referral), payload, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(ReferralResource.objects.count(), 1)

    def test_resource_updates_are_not_supported(self):
        referral = self.create_referral()
        condition = baker.make(
            Condition, patient=self.patient, encounter=self.encounter
        )
        resource = ReferralResource.objects.create(
            referral=referral,
            resource_type="condition",
            resource_id=condition.external_id,
            metadata={"label": "Initial diagnosis"},
        )
        for method in (self.client.put, self.client.patch):
            with self.subTest(method=method.__name__):
                response = method(
                    self.resource_url(referral, resource),
                    {
                        "metadata": {"label": "Confirmed diagnosis"},
                        "attachment_type": "response",
                        "resource_type": "observation",
                        "resource_id": str(uuid.uuid4()),
                    },
                    format="json",
                )
                self.assertEqual(response.status_code, 405, response.data)
                self.assertNotIn("PUT", response["Allow"])
                self.assertNotIn("PATCH", response["Allow"])
                resource.refresh_from_db()
                self.assertEqual(resource.metadata, {"label": "Initial diagnosis"})
                self.assertEqual(resource.attachment_type, "source")
                self.assertEqual(resource.resource_type, "condition")
                self.assertEqual(resource.resource_id, condition.external_id)

    def test_removed_resource_can_be_attached_again(self):
        referral = self.create_referral()
        condition = baker.make(
            Condition, patient=self.patient, encounter=self.encounter
        )
        resource = ReferralResource.objects.create(
            referral=referral,
            resource_type="condition",
            resource_id=condition.external_id,
        )
        response = self.client.delete(self.resource_url(referral, resource))
        self.assertEqual(response.status_code, 204, response.data)
        response = self.client.post(
            self.resource_url(referral),
            {
                "resource_type": "condition",
                "resource_id": str(condition.external_id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(ReferralResource.objects.count(), 1)

    def test_resources_cannot_be_read_or_removed_through_another_referral(self):
        referral = self.create_referral()
        other_referral = self.create_referral(title="Second referral")
        condition = baker.make(
            Condition, patient=self.patient, encounter=self.encounter
        )
        resource = ReferralResource.objects.create(
            referral=referral,
            resource_type="condition",
            resource_id=condition.external_id,
        )
        url = self.resource_url(other_referral, resource)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404, response.data)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 404, response.data)
        self.assertTrue(ReferralResource.objects.filter(id=resource.id).exists())

    def test_referral_thread_and_messages_use_referral_permissions(self):
        referral = self.create_referral()
        response = self.client.post(
            self.referral_url(referral, "thread"),
            {"title": "Referral discussion"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        referral.refresh_from_db()
        self.assertIsNotNone(referral.thread_id)
        self.assertEqual(referral.thread.thread_type, NoteThreadType.referral)
        self.assertEqual(response.data["thread_type"], NoteThreadType.referral)
        response = self.client.post(
            self.note_url(referral), {"message": "Please review today"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.grant_destination(
            ReferralPermissions.can_read_referral.name,
            ReferralPermissions.can_write_referral.name,
            organization=self.destination.default_internal_organization,
        )
        self.client.force_authenticate(user=self.destination_user)
        response = self.client.get(self.note_url(referral))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertContains(response, "Please review today")
        response = self.client.post(
            self.note_url(referral), {"message": "Review booked"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)

    def test_regular_patient_threads_do_not_leak_referral_discussions(self):
        referral = self.create_referral()
        response = self.client.post(
            self.referral_url(referral, "thread"), {}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        referral.refresh_from_db()
        note = NoteMessage.objects.create(
            thread=referral.thread,
            message="Private referral discussion",
            created_by=self.user,
        )
        self.grant_origin(
            PatientPermissions.can_view_clinical_data.name,
            PatientPermissions.can_write_patient.name,
            EncounterPermissions.can_read_encounter_clinical_data.name,
            EncounterPermissions.can_write_encounter_clinical_data.name,
            user=self.outsider,
        )
        self.client.force_authenticate(user=self.outsider)
        response = self.client.get(
            reverse(
                "thread-list", kwargs={"patient_external_id": self.patient.external_id}
            )
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 0)
        response = self.client.get(
            reverse(
                "thread-detail",
                kwargs={
                    "patient_external_id": self.patient.external_id,
                    "external_id": referral.thread.external_id,
                },
            )
        )
        self.assertIn(response.status_code, (403, 404), response.data)
        response = self.client.get(
            reverse(
                "note-detail",
                kwargs={
                    "patient_external_id": self.patient.external_id,
                    "thread_external_id": referral.thread.external_id,
                    "external_id": note.external_id,
                },
            )
        )
        self.assertIn(response.status_code, (403, 404), response.data)

    def test_referral_thread_type_hides_unlinked_threads_from_regular_routes(self):
        user = self.create_super_user()
        self.client.force_authenticate(user=user)
        thread = NoteThread.objects.create(
            title="Private referral discussion",
            patient=self.patient,
            encounter=self.encounter,
            thread_type=NoteThreadType.referral,
            created_by=user,
        )
        ordinary = NoteThread.objects.create(
            title="Patient discussion", patient=self.patient, created_by=user
        )
        note = NoteMessage.objects.create(
            thread=thread, message="Referral message", created_by=user
        )
        self.assertFalse(Referral.objects.filter(thread=thread).exists())
        response = self.client.get(
            reverse(
                "thread-list", kwargs={"patient_external_id": self.patient.external_id}
            )
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            [entry["id"] for entry in response.data["results"]],
            [str(ordinary.external_id)],
        )
        thread_url = reverse(
            "thread-detail",
            kwargs={
                "patient_external_id": self.patient.external_id,
                "external_id": thread.external_id,
            },
        )
        note_kwargs = {
            "patient_external_id": self.patient.external_id,
            "thread_external_id": thread.external_id,
        }
        note_list_url = reverse("note-list", kwargs=note_kwargs)
        note_url = reverse(
            "note-detail", kwargs={**note_kwargs, "external_id": note.external_id}
        )
        for url in (thread_url, note_list_url, note_url):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 404, response.data)
        for method, url, data in (
            (self.client.put, thread_url, {"title": "Changed title"}),
            (self.client.post, note_list_url, {"message": "New message"}),
            (self.client.patch, note_url, {"message": "Changed message"}),
        ):
            with self.subTest(method=method.__name__, url=url):
                response = method(url, data, format="json")
                self.assertEqual(response.status_code, 404, response.data)
        thread.refresh_from_db()
        note.refresh_from_db()
        self.assertEqual(thread.title, "Private referral discussion")
        self.assertEqual(note.message, "Referral message")
        self.assertEqual(NoteMessage.objects.filter(thread=thread).count(), 1)

    def test_referral_writes_cannot_override_the_thread_type(self):
        referral = self.create_referral()
        thread_url = self.referral_url(referral, "thread")
        response = self.client.post(
            thread_url,
            {"title": "Referral discussion", "thread_type": NoteThreadType.patient},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["thread_type"], NoteThreadType.referral)
        referral.refresh_from_db()
        thread = referral.thread
        self.assertEqual(thread.thread_type, NoteThreadType.referral)

        response = self.client.put(
            thread_url,
            {"title": "Updated discussion", "thread_type": NoteThreadType.patient},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["thread_type"], NoteThreadType.referral)
        response = self.client.patch(
            self.referral_url(referral),
            {"note": "Updated referral", "thread_type": NoteThreadType.patient},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        response = self.client.post(
            self.note_url(referral),
            {"message": "Referral message", "thread_type": NoteThreadType.patient},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        note = NoteMessage.objects.get(external_id=response.data["id"])
        for method in (self.client.put, self.client.patch):
            with self.subTest(method=method.__name__):
                response = method(
                    self.note_url(referral, note),
                    {
                        "message": "Updated message",
                        "thread_type": NoteThreadType.patient,
                    },
                    format="json",
                )
                self.assertEqual(response.status_code, 200, response.data)
                thread.refresh_from_db()
                self.assertEqual(thread.thread_type, NoteThreadType.referral)

    def test_referral_message_updates_preserve_author_and_history_rules(self):
        referral = self.create_referral()
        response = self.client.post(
            self.referral_url(referral, "thread"), {}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        referral.refresh_from_db()
        note = NoteMessage.objects.create(
            thread=referral.thread, message="Original", created_by=self.user
        )
        self.grant_destination(
            ReferralPermissions.can_read_referral.name,
            ReferralPermissions.can_write_referral.name,
        )
        self.client.force_authenticate(user=self.destination_user)
        response = self.client.patch(
            self.note_url(referral, note),
            {"message": "Other user's edit"},
            format="json",
        )
        self.assertEqual(response.status_code, 403, response.data)
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            self.note_url(referral, note), {"message": "Updated"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        note.refresh_from_db()
        self.assertEqual(note.message, "Updated")
        self.assertEqual(note.message_history["history"][0]["message"], "Original")

    def test_destination_resolves_current_attached_resource_without_origin_access(self):
        referral = self.create_referral()
        condition = baker.make(
            Condition,
            patient=self.patient,
            encounter=self.encounter,
            code={"code": "finding", "display": "Initial finding"},
            clinical_status="active",
            verification_status="confirmed",
            category="encounter_diagnosis",
            severity="mild",
            note="Initial note",
        )
        attachment_response = self.client.post(
            self.resource_url(referral),
            {"resource_type": "condition", "resource_id": str(condition.external_id)},
            format="json",
        )
        self.assertEqual(attachment_response.status_code, 200, attachment_response.data)
        attachment = ReferralResource.objects.get(
            external_id=attachment_response.data["id"]
        )
        condition.note = "Updated clinical finding"
        condition.save(update_fields=["note"])
        self.grant_destination(
            ReferralPermissions.can_read_referral.name,
            organization=self.destination.default_internal_organization,
        )
        self.client.force_authenticate(user=self.destination_user)
        listed = self.client.get(self.resource_url(referral))
        self.assertEqual(listed.status_code, 200, listed.data)
        self.assertEqual(listed.data["count"], 1)
        retrieved = self.client.get(self.resource_url(referral, attachment))
        self.assertEqual(retrieved.status_code, 200, retrieved.data)
        response = self.client.get(
            reverse(
                "referral-resource-resolve",
                kwargs={
                    "referral_external_id": referral.external_id,
                    "external_id": attachment.external_id,
                },
            )
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["resource"]["id"], str(condition.external_id))
        self.assertEqual(response.data["resource"]["note"], "Updated clinical finding")
        denied = self.client.post(
            self.resource_url(referral),
            {"resource_type": "condition", "resource_id": str(condition.external_id)},
            format="json",
        )
        self.assertEqual(denied.status_code, 403, denied.data)
        for method in (self.client.put, self.client.patch):
            denied = method(
                self.resource_url(referral, attachment),
                {"metadata": {"label": "Not allowed"}},
                format="json",
            )
            self.assertEqual(denied.status_code, 405, denied.data)
        denied = self.client.delete(self.resource_url(referral, attachment))
        self.assertEqual(denied.status_code, 403, denied.data)
        attachment.refresh_from_db()
        self.assertEqual(attachment.metadata, {})
        response = self.client.get(
            reverse(
                "diagnosis-detail",
                kwargs={
                    "patient_external_id": self.patient.external_id,
                    "external_id": condition.external_id,
                },
            ),
            {"encounter": str(self.encounter.external_id)},
        )
        self.assertEqual(response.status_code, 403, response.data)

    def test_resource_resolution_denies_outsider_and_cross_referral_paths(self):
        referral = self.create_referral()
        other_referral = self.create_referral(title="Other referral")
        condition = baker.make(
            Condition, patient=self.patient, encounter=self.encounter
        )
        attachment = ReferralResource.objects.create(
            referral=referral,
            resource_type="condition",
            resource_id=condition.external_id,
        )
        response = self.client.get(
            reverse(
                "referral-resource-resolve",
                kwargs={
                    "referral_external_id": other_referral.external_id,
                    "external_id": attachment.external_id,
                },
            )
        )
        self.assertEqual(response.status_code, 404, response.data)
        self.client.force_authenticate(user=self.outsider)
        response = self.client.get(
            reverse(
                "referral-resource-resolve",
                kwargs={
                    "referral_external_id": referral.external_id,
                    "external_id": attachment.external_id,
                },
            )
        )
        self.assertIn(response.status_code, (403, 404), response.data)

        denied = self.client.post(
            self.resource_url(referral),
            {"resource_type": "condition", "resource_id": str(condition.external_id)},
            format="json",
        )
        self.assertEqual(denied.status_code, 403, denied.data)
        for method in (self.client.put, self.client.patch):
            denied = method(
                self.resource_url(referral, attachment),
                {"metadata": {"label": "Not allowed"}},
                format="json",
            )
            self.assertEqual(denied.status_code, 405, denied.data)
        denied = self.client.delete(self.resource_url(referral, attachment))
        self.assertEqual(denied.status_code, 403, denied.data)
        attachment.refresh_from_db()
        self.assertEqual(attachment.metadata, {})

    def test_deleted_sources_and_removed_attachments_cannot_be_resolved(self):
        referral = self.create_referral()
        condition = baker.make(
            Condition, patient=self.patient, encounter=self.encounter
        )
        attachment = ReferralResource.objects.create(
            referral=referral,
            resource_type="condition",
            resource_id=condition.external_id,
        )
        resolve_url = reverse(
            "referral-resource-resolve",
            kwargs={
                "referral_external_id": referral.external_id,
                "external_id": attachment.external_id,
            },
        )
        condition.delete()
        response = self.client.get(resolve_url)
        self.assertEqual(response.status_code, 404, response.data)
        condition.deleted = False
        condition.save(update_fields=["deleted"])
        attachment.delete()
        response = self.client.get(resolve_url)
        self.assertEqual(response.status_code, 404, response.data)

    def test_set_assignees_action_can_assign_and_clear_the_inbox(self):
        referral = self.create_referral()
        url = self.referral_url(referral, "set-assignees")
        response = self.client.post(
            url,
            {
                "members": [
                    {
                        "user_id": str(self.user.external_id),
                        "role": {"system": "http://snomed.info/sct", "code": "doctor"},
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        referral.refresh_from_db()
        self.assertEqual(referral.assignee_users, [self.user.id])
        response = self.client.post(url, {"members": []}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        referral.refresh_from_db()
        self.assertEqual(referral.assignees, [])
        self.assertEqual(referral.assignee_users, [])

    def test_thread_title_update_and_notes_without_a_thread(self):
        referral = self.create_referral()
        response = self.client.post(
            self.note_url(referral), {"message": "Cannot post yet"}, format="json"
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(NoteMessage.objects.exists())
        response = self.client.get(self.note_url(referral))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 0)
        url = self.referral_url(referral, "thread")
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        response = self.client.put(url, {"title": "Referral follow-up"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["title"], "Referral follow-up")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405, response.data)
        referral.refresh_from_db()
        self.assertEqual(referral.thread.title, "Referral follow-up")
        response = self.client.get(self.referral_url(referral))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["thread"], str(referral.thread.external_id))

    def test_partial_availability_update_preserves_then_clears_form_mapping(self):
        self.grant_destination(
            ReferralPermissions.can_manage_referral_availability.name
        )
        self.client.force_authenticate(user=self.destination_user)
        response = self.client.patch(
            self.availability_url(self.availability),
            {"description": "Revised instructions"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data["questionnaires"]), 1)
        response = self.client.patch(
            self.availability_url(self.availability),
            {"questionnaires": [], "is_public": False},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["questionnaires"], [])
        self.assertFalse(response.data["is_public"])
        self.availability.refresh_from_db()
        self.assertFalse(self.availability.questionnaires.exists())
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.availability_url())
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 0)

    def test_external_entity_is_immutable_for_all_destination_types(self):
        self.grant_destination(
            ReferralPermissions.can_manage_referral_availability.name
        )
        self.client.force_authenticate(user=self.destination_user)
        response = self.client.patch(
            self.availability_url(self.availability),
            {"external_entity": {"name": "Invalid external details"}},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["external_entity"], {})
        self.availability.refresh_from_db()
        self.assertEqual(self.availability.external_entity, {})
        external_availability = ReferralAvailability.objects.create(
            entity_type="external",
            external_entity={"name": "External specialist"},
            name="External referral",
            status="active",
            referral_type="consultation",
            created_by=self.destination_user,
        )
        for details in ({}, {"name": "Changed external specialist"}):
            with self.subTest(details=details):
                response = self.client.patch(
                    self.availability_url(external_availability),
                    {"external_entity": details},
                    format="json",
                )
                self.assertIn(response.status_code, (403, 404), response.data)
                external_availability.refresh_from_db()
                self.assertEqual(
                    external_availability.external_entity,
                    {"name": "External specialist"},
                )
