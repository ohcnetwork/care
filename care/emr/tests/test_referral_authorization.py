from django.contrib.auth.models import AnonymousUser
from django.urls import reverse
from model_bakery import baker

from care.emr.models.diagnostic_report import DiagnosticReport
from care.emr.models.location import FacilityLocation, FacilityLocationOrganization
from care.emr.models.patient import PatientUser
from care.emr.models.questionnaire import Questionnaire, QuestionnaireResponse
from care.emr.models.referral import Referral, ReferralAvailability, ReferralResource
from care.emr.models.specimen import Specimen
from care.security.authorization.referral import ReferralAccess
from care.security.permissions.diagnostic_report import DiagnosticReportPermissions
from care.security.permissions.encounter import EncounterPermissions
from care.security.permissions.patient import PatientPermissions
from care.security.permissions.referral import ReferralPermissions
from care.security.permissions.service_request import ServiceRequestPermissions
from care.security.permissions.specimen import SpecimenPermissions
from care.utils.tests.base import CareAPITestBase


class ReferralAuthorizationTestCase(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.access = ReferralAccess()
        self.user = self.create_user()
        self.publisher = self.create_user()
        self.origin = self.create_facility(user=self.publisher)
        self.origin_org = self.create_facility_organization(facility=self.origin)
        self.destination = self.create_facility(user=self.publisher)
        self.patient = self.create_patient()
        self.encounter = self.create_encounter(
            patient=self.patient, facility=self.origin, organization=self.origin_org
        )
        self.questionnaire = baker.make(
            Questionnaire,
            subject_type="encounter",
            status="active",
            questions=[],
        )

    def availability(self, entity_type="facility", **kwargs):
        target = {"facility": self.destination} if entity_type == "facility" else {}
        return ReferralAvailability.objects.create(
            entity_type=entity_type,
            name="Referral service",
            status="active",
            referral_type="consultation",
            created_by=self.publisher,
            **target,
            **kwargs,
        )

    def referral(self, availability, **kwargs):
        encounter = kwargs.pop("encounter", self.encounter)
        patient = kwargs.pop(
            "patient", encounter.patient if encounter else self.patient
        )
        return Referral.objects.create(
            availability=availability,
            patient=patient,
            encounter=encounter,
            title="Referral",
            **kwargs,
        )

    def grant(self, organization, *, internal=False, user=None, permissions=None):
        role = self.create_role_with_permissions(
            permissions=permissions
            or [
                ReferralPermissions.can_manage_referral_availability.name,
                ReferralPermissions.can_read_referral_availability.name,
                ReferralPermissions.can_submit_referral_availability.name,
                ReferralPermissions.can_create_referral.name,
                ReferralPermissions.can_read_referral.name,
                ReferralPermissions.can_write_referral.name,
            ]
        )
        attach = (
            self.attach_role_facility_organization_user
            if internal
            else self.attach_role_organization_user
        )
        return attach(organization, user or self.user, role)

    def assert_available_to_user(
        self, availability, *, allowed, selectable=None, user=None
    ):
        user = user or self.user
        self.assertEqual(
            self.access.can_view_referral_availability(user, availability), allowed
        )
        self.assertEqual(
            self.access.get_accessible_referral_availabilities(
                ReferralAvailability.objects.all(), user, availability.entity_type
            )
            .filter(id=availability.id)
            .exists(),
            allowed if selectable is None else selectable,
        )

    def assert_referral_access(self, referral, *, allowed):
        self.assertEqual(self.access.can_read_referral(self.user, referral), allowed)
        self.assertEqual(self.access.can_write_referral(self.user, referral), allowed)

    def destination_organization(self, internal, **kwargs):
        if internal:
            return self.create_facility_organization(
                facility=self.destination, **kwargs
            )
        return self.create_organization(**kwargs)

    def test_availability_selection_is_scoped_to_the_requested_entity_type(self):
        availabilities = [
            self.availability(is_public=True),
            self.availability(
                "internal_organization",
                internal_organization=self.destination.default_internal_organization,
                is_public=True,
            ),
            self.availability(
                "external_organization",
                external_organization=self.create_organization(),
                is_public=True,
            ),
        ]
        for user in (self.user, self.create_super_user()):
            for availability in availabilities:
                with self.subTest(user=user.id, entity_type=availability.entity_type):
                    selected = self.access.get_accessible_referral_availabilities(
                        ReferralAvailability.objects.all(),
                        user,
                        availability.entity_type,
                    )
                    self.assertQuerySetEqual(selected, [availability], ordered=False)

    def test_facility_availability_requires_a_root_organization_membership(self):
        availability = self.availability()
        department = self.create_facility_organization(
            facility=self.destination,
            parent=self.destination.default_internal_organization,
            org_type="dept",
        )
        self.grant(department, internal=True)
        self.assert_available_to_user(availability, allowed=False)
        self.assertFalse(
            self.access.can_manage_referral_availability(self.user, availability)
        )
        self.assertFalse(
            self.access.can_submit_referral_availability(self.user, availability)
        )

        self.grant(self.destination.default_internal_organization, internal=True)
        self.assert_available_to_user(availability, allowed=True)
        self.assertTrue(
            self.access.can_manage_referral_availability(self.user, availability)
        )
        self.assertTrue(
            self.access.can_submit_referral_availability(self.user, availability)
        )

    def test_availability_managers_and_superusers_cannot_select_drafts_or_inactive(
        self,
    ):
        availability = self.availability()
        self.grant(
            self.destination.default_internal_organization,
            internal=True,
            permissions=[ReferralPermissions.can_manage_referral_availability.name],
        )
        for user in (self.user, self.create_super_user()):
            availability.status = "active"
            availability.save()
            self.assert_available_to_user(availability, allowed=True, user=user)
            for status in ("draft", "inactive"):
                with self.subTest(user=user.id, status=status):
                    availability.status = status
                    availability.save()
                    self.assertTrue(
                        self.access.can_manage_referral_availability(user, availability)
                    )
                    self.assert_available_to_user(
                        availability, allowed=True, selectable=False, user=user
                    )

    def test_legacy_external_availability_selection_is_limited_to_superusers(self):
        availability = self.availability(
            "external", external_entity={"name": "External destination"}
        )
        superuser = self.create_super_user()
        for is_public in (False, True):
            availability.is_public = is_public
            availability.save()
            for user in (self.user, self.publisher, superuser):
                with self.subTest(is_public=is_public, user=user.id):
                    selected = self.access.get_accessible_referral_availabilities(
                        ReferralAvailability.objects.all(), user, "external"
                    )
                    self.assertEqual(selected.exists(), user.is_superuser)

    def test_external_organization_ancestor_permission_includes_child_only(self):
        root = self.create_organization()
        child = self.create_organization(parent=root)
        unrelated = self.create_organization()
        child_availability = self.availability(
            "external_organization", external_organization=child
        )
        unrelated_availability = self.availability(
            "external_organization", external_organization=unrelated
        )
        self.grant(root)
        self.assert_available_to_user(child_availability, allowed=True)
        self.assertTrue(
            self.access.can_manage_referral_availability(self.user, child_availability)
        )
        self.assertTrue(
            self.access.can_submit_referral_availability(self.user, child_availability)
        )
        self.assert_referral_access(self.referral(child_availability), allowed=True)
        self.assert_available_to_user(unrelated_availability, allowed=False)
        self.assert_referral_access(
            self.referral(unrelated_availability), allowed=False
        )

    def test_internal_organization_ancestor_permission_includes_child_only(self):
        root = self.create_facility_organization(facility=self.destination)
        child = self.create_facility_organization(
            facility=self.destination, parent=root
        )
        unrelated = self.create_facility_organization(facility=self.destination)
        child_availability = self.availability(
            "internal_organization", internal_organization=child
        )
        unrelated_availability = self.availability(
            "internal_organization", internal_organization=unrelated
        )
        self.grant(root, internal=True)
        self.assert_available_to_user(child_availability, allowed=True)
        self.assertTrue(
            self.access.can_manage_referral_availability(self.user, child_availability)
        )
        self.assert_referral_access(self.referral(child_availability), allowed=True)
        self.assert_available_to_user(unrelated_availability, allowed=False)
        self.assert_referral_access(
            self.referral(unrelated_availability), allowed=False
        )

    def test_child_organization_permission_does_not_include_parent_or_sibling(self):
        for internal in (False, True):
            with self.subTest(internal=internal):
                root = self.destination_organization(internal)
                child = self.destination_organization(internal, parent=root)
                sibling = self.destination_organization(internal, parent=root)
                self.grant(child, internal=internal)
                entity_type = (
                    "internal_organization" if internal else "external_organization"
                )
                for organization in (root, sibling):
                    availability = self.availability(
                        entity_type, **{entity_type: organization}
                    )
                    self.assert_available_to_user(availability, allowed=False)
                    self.assert_referral_access(
                        self.referral(availability), allowed=False
                    )

    def test_origin_location_permission_matches_detail_and_list_and_is_revocable(self):
        location_org = self.create_facility_organization(facility=self.origin)
        location = baker.make(FacilityLocation, facility=self.origin)
        FacilityLocationOrganization.objects.create(
            location=location, organization=location_org
        )
        self.encounter.current_location = location
        self.encounter.save()
        availability = self.availability(is_public=True)
        referral = self.referral(availability)
        self.grant(location_org, internal=True)
        self.assertTrue(
            self.access.can_create_referral(self.user, self.encounter, availability)
        )
        self.assert_referral_access(referral, allowed=True)
        self.encounter.current_location = None
        self.encounter.save()
        referral.refresh_from_db()
        self.assertFalse(
            self.access.can_create_referral(self.user, self.encounter, availability)
        )
        self.assert_referral_access(referral, allowed=False)

    def test_patient_origin_uses_direct_patient_roles_and_private_destination_access(
        self,
    ):
        availability = self.availability(is_public=True)
        referral = self.referral(availability, encounter=None)
        unrelated = self.referral(
            availability, encounter=None, patient=self.create_patient()
        )
        role = self.create_role_with_permissions(
            permissions=[
                ReferralPermissions.can_create_referral.name,
                ReferralPermissions.can_read_referral.name,
                ReferralPermissions.can_write_referral.name,
            ]
        )
        membership = PatientUser.objects.create(
            patient=self.patient, user=self.user, role=role
        )
        self.assertTrue(
            self.access.can_create_referral(
                self.user, None, availability, patient=self.patient
            )
        )
        self.assert_referral_access(referral, allowed=True)
        self.assert_referral_access(unrelated, allowed=False)
        self.assertFalse(
            self.access.can_create_referral(
                self.user, None, availability, patient=unrelated.patient
            )
        )

        availability.is_public = False
        availability.save()
        self.assertFalse(
            self.access.can_create_referral(
                self.user, None, availability, patient=self.patient
            )
        )
        destination_org = self.destination.default_internal_organization
        self.grant(
            destination_org,
            internal=True,
            permissions=[ReferralPermissions.can_submit_referral_availability.name],
        )
        self.assertTrue(
            self.access.can_create_referral(
                self.user, None, availability, patient=self.patient
            )
        )
        membership.delete()
        self.assert_referral_access(referral, allowed=False)

    def test_patient_origin_uses_patient_organization_ancestor_roles(self):
        organization = self.create_organization()
        child = self.create_organization(parent=organization)
        self.patient.geo_organization = child
        self.patient.save()
        availability = self.availability(is_public=True)
        referral = self.referral(availability, encounter=None)
        self.grant(organization)
        self.assertTrue(
            self.access.can_create_referral(
                self.user, None, availability, patient=self.patient
            )
        )
        self.assert_referral_access(referral, allowed=True)
        self.assert_referral_access(
            self.referral(availability, encounter=None, patient=self.create_patient()),
            allowed=False,
        )

    def test_patient_origin_active_encounter_location_access_is_revocable(self):
        location_org = self.create_facility_organization(facility=self.origin)
        location = baker.make(FacilityLocation, facility=self.origin)
        FacilityLocationOrganization.objects.create(
            location=location, organization=location_org
        )
        self.encounter.current_location = location
        self.encounter.save()
        self.grant(location_org, internal=True)
        availability = self.availability(is_public=True)
        patient_referral = self.referral(availability, encounter=None)
        encounter_referral = self.referral(availability)
        self.assert_referral_access(patient_referral, allowed=True)
        self.assertTrue(
            self.access.can_create_referral(
                self.user, None, availability, patient=self.patient
            )
        )
        self.encounter.status = "completed"
        self.encounter.save()
        self.assert_referral_access(patient_referral, allowed=False)
        self.assertFalse(
            self.access.can_create_referral(
                self.user, None, availability, patient=self.patient
            )
        )
        self.assert_referral_access(encounter_referral, allowed=True)

    def test_patient_visibility_does_not_grant_referral_permissions(self):
        role = self.create_role_with_permissions(
            permissions=[
                PatientPermissions.can_list_patients.name,
                PatientPermissions.can_write_patient.name,
            ]
        )
        PatientUser.objects.create(patient=self.patient, user=self.user, role=role)
        availability = self.availability(is_public=True)
        referral = self.referral(availability, encounter=None)
        self.assertFalse(
            self.access.can_create_referral(
                self.user, None, availability, patient=self.patient
            )
        )
        self.assert_referral_access(referral, allowed=False)

    def test_patient_origin_permissions_remain_separate_and_encounter_scope_is_unchanged(
        self,
    ):
        role = self.create_role_with_permissions(
            permissions=[ReferralPermissions.can_create_referral.name]
        )
        membership = PatientUser.objects.create(
            patient=self.patient, user=self.user, role=role
        )
        availability = self.availability(is_public=True)
        referral = self.referral(availability, encounter=None)
        self.assertTrue(
            self.access.can_create_referral(
                self.user, None, availability, patient=self.patient
            )
        )
        self.assert_referral_access(referral, allowed=False)
        membership.role = self.create_role_with_permissions(
            permissions=[ReferralPermissions.can_read_referral.name]
        )
        membership.save()
        self.assertTrue(self.access.can_read_referral(self.user, referral))
        self.assertFalse(self.access.can_write_referral(self.user, referral))
        self.assertFalse(
            self.access.can_create_referral(
                self.user, None, availability, patient=self.patient
            )
        )
        encounter_referral = self.referral(availability)
        self.assert_referral_access(encounter_referral, allowed=False)

    def test_patient_origin_destination_permissions_do_not_require_patient_access(self):
        availability = self.availability()
        referral = self.referral(availability, encounter=None)
        destination_org = self.destination.default_internal_organization
        self.grant(destination_org, internal=True)
        self.assert_referral_access(referral, allowed=True)
        self.assertFalse(
            self.access.can_create_referral(
                self.user, None, availability, patient=self.patient
            )
        )

    def test_patient_origin_does_not_grant_access_from_creator_or_assignee_membership(
        self,
    ):
        availability = self.availability(is_public=True)
        referral = self.referral(
            availability,
            encounter=None,
            created_by=self.user,
            assignees=[{"user_id": self.user.id}],
        )
        self.assert_referral_access(referral, allowed=False)

    def test_patient_origin_handles_anonymous_and_superusers(self):
        availability = self.availability(is_public=True)
        referral = self.referral(availability, encounter=None)
        anonymous = AnonymousUser()
        self.assertFalse(self.access.can_read_referral(anonymous, referral))
        self.assertFalse(self.access.can_write_referral(anonymous, referral))
        self.assertFalse(
            self.access.can_create_referral(
                anonymous, None, availability, patient=self.patient
            )
        )
        superuser = self.create_super_user()
        self.assertTrue(self.access.can_read_referral(superuser, referral))
        self.assertTrue(self.access.can_write_referral(superuser, referral))
        self.assertTrue(
            self.access.can_create_referral(
                superuser, None, availability, patient=self.patient
            )
        )

    def test_assignment_caches_do_not_grant_availability_or_referral_access(self):
        availability = self.availability(care_team=[{"user_id": self.user.id}])
        referral = self.referral(availability, assignees=[{"user_id": self.user.id}])
        self.assertEqual(referral.assignee_users, [self.user.id])
        self.assert_available_to_user(availability, allowed=False)
        self.assert_referral_access(referral, allowed=False)
        availability.is_public = True
        availability.save()
        self.assert_available_to_user(availability, allowed=True)
        self.assert_referral_access(referral, allowed=False)

    def test_private_reader_cannot_view_drafts_or_inactive_availability(self):
        organization = self.destination.default_internal_organization
        availability = self.availability()
        self.grant(
            organization,
            internal=True,
            permissions=[
                ReferralPermissions.can_read_referral_availability.name,
                ReferralPermissions.can_submit_referral_availability.name,
            ],
        )
        self.assert_available_to_user(availability, allowed=True)
        for status in ("draft", "inactive"):
            with self.subTest(status=status):
                availability.status = status
                availability.is_public = True
                availability.save()
                self.assert_available_to_user(availability, allowed=False)
                self.assertFalse(
                    self.access.can_submit_referral_availability(
                        self.user, availability
                    )
                )

    def test_anonymous_user_cannot_read_public_availability_or_referrals(self):
        availability = self.availability(is_public=True)
        referral = self.referral(availability)
        anonymous = AnonymousUser()
        self.assertFalse(
            self.access.can_view_referral_availability(anonymous, availability)
        )
        self.assertFalse(
            self.access.can_submit_referral_availability(anonymous, availability)
        )
        self.assertFalse(self.access.can_read_referral(anonymous, referral))
        self.assertFalse(
            self.access.get_accessible_referral_availabilities(
                ReferralAvailability.objects.all(), anonymous, availability.entity_type
            ).exists()
        )

    def test_attachment_requires_the_source_resources_read_permission(self):
        self.grant(
            self.origin_org,
            internal=True,
            permissions=[
                ReferralPermissions.can_read_referral.name,
                ReferralPermissions.can_write_referral.name,
                PatientPermissions.can_view_clinical_data.name,
                EncounterPermissions.can_read_encounter_clinical_data.name,
            ],
        )
        referral = self.referral(self.availability(is_public=True))
        service_request = self.create_service_request(
            patient=self.patient, facility=self.origin, encounter=self.encounter
        )
        specimen = baker.make(
            Specimen,
            patient=self.patient,
            encounter=self.encounter,
            service_request=service_request,
        )
        report = baker.make(
            DiagnosticReport,
            patient=self.patient,
            encounter=self.encounter,
            service_request=service_request,
        )
        response = baker.make(
            QuestionnaireResponse,
            patient=self.patient,
            encounter=None,
            questionnaire=self.questionnaire,
        )
        self.client.force_authenticate(user=self.user)
        url = reverse(
            "referral-resource-list",
            kwargs={"referral_external_id": referral.external_id},
        )
        cases = [
            ("specimen", specimen, SpecimenPermissions.can_read_specimen.name),
            (
                "diagnostic_report",
                report,
                DiagnosticReportPermissions.can_read_diagnostic_report.name,
            ),
            (
                "service_request",
                service_request,
                ServiceRequestPermissions.can_read_service_request.name,
            ),
            (
                "questionnaire_response",
                response,
                PatientPermissions.can_view_questionnaire_responses.name,
            ),
        ]
        for resource_type, resource, permission in cases:
            with self.subTest(resource_type=resource_type):
                payload = {
                    "resource_type": resource_type,
                    "resource_id": str(resource.external_id),
                }
                denied = self.client.post(url, payload, format="json")
                self.assertEqual(denied.status_code, 403, denied.data)
                self.assertFalse(
                    ReferralResource.objects.filter(
                        referral=referral, resource_id=resource.external_id
                    ).exists()
                )
                self.grant(self.origin_org, internal=True, permissions=[permission])
                allowed = self.client.post(url, payload, format="json")
                self.assertEqual(allowed.status_code, 200, allowed.data)

    def test_resolving_a_report_does_not_include_unattached_related_resources(self):
        availability = self.availability()
        referral = self.referral(availability)
        service_request = self.create_service_request(
            patient=self.patient, facility=self.origin, encounter=self.encounter
        )
        report = baker.make(
            DiagnosticReport,
            patient=self.patient,
            encounter=self.encounter,
            service_request=service_request,
            conclusion="Specialist finding",
        )
        attachment = ReferralResource.objects.create(
            referral=referral,
            resource_type="diagnostic_report",
            resource_id=report.external_id,
        )
        destination_org = self.destination.default_internal_organization
        self.grant(
            destination_org,
            internal=True,
            permissions=[ReferralPermissions.can_read_referral.name],
        )
        self.client.force_authenticate(user=self.user)
        url = reverse(
            "referral-resource-resolve",
            kwargs={
                "referral_external_id": referral.external_id,
                "external_id": attachment.external_id,
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["resource_type"], "diagnostic_report")
        self.assertEqual(response.data["resource"]["id"], str(report.external_id))
        self.assertEqual(response.data["resource"]["conclusion"], report.conclusion)
        for related in ("patient", "encounter", "observations", "service_request"):
            self.assertNotIn(related, response.data["resource"])

        another_referral = self.referral(availability)
        wrong_url = reverse(
            "referral-resource-resolve",
            kwargs={
                "referral_external_id": another_referral.external_id,
                "external_id": attachment.external_id,
            },
        )
        response = self.client.get(wrong_url)
        self.assertEqual(response.status_code, 404, response.data)

    def test_specimen_without_service_request_is_denied_cleanly(self):
        self.grant(self.origin_org, internal=True)
        referral = self.referral(self.availability())
        specimen = baker.make(
            Specimen,
            patient=self.patient,
            encounter=self.encounter,
            service_request=None,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            reverse(
                "referral-resource-list",
                kwargs={"referral_external_id": referral.external_id},
            ),
            {
                "resource_type": "specimen",
                "resource_id": str(specimen.external_id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403, response.data)
        self.assertFalse(ReferralResource.objects.exists())
