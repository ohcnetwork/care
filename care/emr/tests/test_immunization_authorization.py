from model_bakery import baker

from care.emr.models.location import FacilityLocation, FacilityLocationOrganization
from care.emr.models.patient import PatientUser
from care.emr.resources.encounter.constants import StatusChoices
from care.security.authorization.immunization import ImmunizationAccess
from care.security.permissions.immunization import ImmunizationPermissions
from care.utils.tests.base import CareAPITestBase


class ImmunizationAuthorizationTests(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.access = ImmunizationAccess()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.patient = self.create_patient()
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )

    def grant(self, *permissions, organization=None):
        role = self.create_role_with_permissions(list(permissions))
        self.attach_role_facility_organization_user(
            organization or self.organization, self.user, role
        )
        return role

    def test_unrelated_facility_role_cannot_access_patient_or_encounter(self):
        other_facility = self.create_facility(user=self.user)
        other_organization = self.create_facility_organization(facility=other_facility)
        self.grant(
            *(permission.name for permission in ImmunizationPermissions),
            organization=other_organization,
        )
        for action in (
            "can_read_patient_immunization",
            "can_read_patient_immunization_recommendation",
            "can_write_patient_immunization_recommendation",
        ):
            with self.subTest(action=action):
                self.assertFalse(getattr(self.access, action)(self.user, self.patient))
        for action in (
            "can_read_encounter_immunization",
            "can_write_encounter_immunization",
            "can_read_encounter_immunization_recommendation",
            "can_write_encounter_immunization_recommendation",
        ):
            with self.subTest(action=action):
                self.assertFalse(
                    getattr(self.access, action)(self.user, self.encounter)
                )

    def test_patient_association_grants_patient_access_without_encounter_write(self):
        role = self.create_role_with_permissions(
            [
                ImmunizationPermissions.can_read_immunization.name,
                ImmunizationPermissions.can_read_immunization_recommendation.name,
                ImmunizationPermissions.can_write_immunization_recommendation.name,
                ImmunizationPermissions.can_write_immunization.name,
            ]
        )
        PatientUser.objects.create(patient=self.patient, user=self.user, role=role)
        self.assertTrue(
            self.access.can_read_patient_immunization(self.user, self.patient)
        )
        self.assertTrue(
            self.access.can_read_patient_immunization_recommendation(
                self.user, self.patient
            )
        )
        self.assertTrue(
            self.access.can_write_patient_immunization_recommendation(
                self.user, self.patient
            )
        )
        self.assertFalse(
            self.access.can_write_encounter_immunization(self.user, self.encounter)
        )

    def test_read_permission_does_not_grant_write(self):
        self.grant(
            ImmunizationPermissions.can_read_immunization.name,
            ImmunizationPermissions.can_read_immunization_recommendation.name,
        )
        self.assertTrue(
            self.access.can_read_patient_immunization(self.user, self.patient)
        )
        self.assertTrue(
            self.access.can_read_encounter_immunization(self.user, self.encounter)
        )
        self.assertFalse(
            self.access.can_write_encounter_immunization(self.user, self.encounter)
        )
        self.assertFalse(
            self.access.can_write_patient_immunization_recommendation(
                self.user, self.patient
            )
        )

    def test_current_location_roles_grant_encounter_access(self):
        organization = self.create_facility_organization(facility=self.facility)
        location = baker.make(FacilityLocation, facility=self.facility)
        FacilityLocationOrganization.objects.create(
            location=location, organization=organization
        )
        self.encounter.current_location = location
        self.encounter.save(update_fields=["current_location"])
        self.grant(
            ImmunizationPermissions.can_read_immunization.name,
            ImmunizationPermissions.can_write_immunization.name,
            ImmunizationPermissions.can_read_immunization_recommendation.name,
            ImmunizationPermissions.can_write_immunization_recommendation.name,
            organization=organization,
        )
        self.assertTrue(
            self.access.can_read_encounter_immunization(self.user, self.encounter)
        )
        self.assertTrue(
            self.access.can_write_encounter_immunization(self.user, self.encounter)
        )
        self.assertTrue(
            self.access.can_read_encounter_immunization_recommendation(
                self.user, self.encounter
            )
        )
        self.assertTrue(
            self.access.can_write_encounter_immunization_recommendation(
                self.user, self.encounter
            )
        )

    def test_closed_encounters_cannot_be_written_even_by_superuser(self):
        self.grant(
            ImmunizationPermissions.can_write_immunization.name,
            ImmunizationPermissions.can_write_immunization_recommendation.name,
        )
        self.encounter.status = StatusChoices.completed.value
        self.encounter.save(update_fields=["status"])
        for user in (self.user, self.create_super_user()):
            with self.subTest(user=user.id):
                self.assertFalse(
                    self.access.can_write_encounter_immunization(user, self.encounter)
                )
                self.assertFalse(
                    self.access.can_write_encounter_immunization_recommendation(
                        user, self.encounter
                    )
                )

    def test_facility_policy_write_requires_root_membership(self):
        self.grant(
            ImmunizationPermissions.can_read_immunization_policy.name,
            ImmunizationPermissions.can_write_immunization_policy.name,
        )
        self.assertTrue(
            self.access.can_list_facility_immunization_policy(self.user, self.facility)
        )
        self.assertFalse(
            self.access.can_write_facility_immunization_policy(self.user, self.facility)
        )
        self.grant(
            ImmunizationPermissions.can_write_immunization_policy.name,
            organization=self.facility.default_internal_organization,
        )
        self.assertTrue(
            self.access.can_write_facility_immunization_policy(self.user, self.facility)
        )
