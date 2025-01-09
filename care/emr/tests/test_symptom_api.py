from django.urls import reverse
from polyfactory.factories.pydantic_factory import ModelFactory

from care.emr.resources.condition.spec import ConditionSpec
from care.emr.resources.resource_request.spec import StatusChoices
from care.security.permissions.encounter import EncounterPermissions
from care.security.permissions.patient import PatientPermissions
from care.utils.tests.base import CareAPITestBase


class ConditionFactory(ModelFactory[ConditionSpec]):
    __model__ = ConditionSpec


class TestSymptomViewset(CareAPITestBase):
    def setUp(self):
        """Set up test data for all tests"""
        super().setUp()
        self.user = self.create_user()
        self.client.force_authenticate(user=self.user)
        self.patient = self.create_patient()
        self.base_url = reverse(
            "symptom-list", kwargs={"patient_external_id": self.patient.external_id}
        )

    def generate_symptom_data(self, encounter_id, **kwargs):
        return ConditionFactory.build(encounter=encounter_id, **kwargs)

    def test_list_symptoms_with_permissions(self):
        user = self.create_user()
        role = self.create_role_with_permissions(
            permissions=[PatientPermissions.can_view_clinical_data.name],
        )

        facility = self.create_facility(user=user)
        organization = self.create_facility_organization(facility=facility)
        self.attach_role_facility_organization_user(organization, user, role)
        self.encounter = self.create_encounter(
            patient=self.patient, facility=facility, organization=organization
        )

        self.client.force_authenticate(user=user)
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)

    def test_list_symptoms_with_permissions_and_encounter_status_as_completed(self):
        user = self.create_user()
        role = self.create_role_with_permissions(
            permissions=[PatientPermissions.can_view_clinical_data.name],
        )

        facility = self.create_facility(user=user)
        organization = self.create_facility_organization(facility=facility)
        self.attach_role_facility_organization_user(organization, user, role)
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=facility,
            organization=organization,
            status=StatusChoices.completed.value,
        )

        self.client.force_authenticate(user=user)
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 403)

    def test_list_symptoms_without_permissions(self):
        user = self.create_user()
        role = self.create_role_with_permissions(permissions=[])

        facility = self.create_facility(user=user)
        organization = self.create_facility_organization(facility=facility)
        self.attach_role_facility_organization_user(organization, user, role)
        self.encounter = self.create_encounter(
            patient=self.patient, facility=facility, organization=organization
        )

        self.client.force_authenticate(user=user)
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 403)

    def test_list_symptoms_for_single_encounter_with_permissions(self):
        user = self.create_user()
        role = self.create_role_with_permissions(
            permissions=[EncounterPermissions.can_read_encounter.name],
        )

        facility = self.create_facility(user=user)
        organization = self.create_facility_organization(facility=facility)
        self.attach_role_facility_organization_user(organization, user, role)
        self.encounter = self.create_encounter(
            patient=self.patient, facility=facility, organization=organization
        )

        self.client.force_authenticate(user=user)
        response = self.client.get(
            f"{self.base_url}?encounter={self.encounter.external_id}"
        )
        self.assertEqual(response.status_code, 200)

    def test_list_symptoms_for_single_encounter_with_permissions_and_encounter_status_completed(
        self,
    ):
        user = self.create_user()
        role = self.create_role_with_permissions(
            permissions=[EncounterPermissions.can_read_encounter.name],
        )

        facility = self.create_facility(user=user)
        organization = self.create_facility_organization(facility=facility)
        self.attach_role_facility_organization_user(organization, user, role)
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=facility,
            organization=organization,
            status=StatusChoices.completed.value,
        )

        self.client.force_authenticate(user=user)
        response = self.client.get(
            f"{self.base_url}?encounter={self.encounter.external_id}"
        )
        self.assertEqual(response.status_code, 200)

    def test_list_symptoms_for_single_encounter_without_permissions(self):
        user = self.create_user()
        role = self.create_role_with_permissions(permissions=[])

        facility = self.create_facility(user=user)
        organization = self.create_facility_organization(facility=facility)
        self.attach_role_facility_organization_user(organization, user, role)
        self.encounter = self.create_encounter(
            patient=self.patient, facility=facility, organization=organization
        )

        self.client.force_authenticate(user=user)
        response = self.client.get(
            f"{self.base_url}?encounter={self.encounter.external_id}"
        )
        self.assertEqual(response.status_code, 403)

    def test_create_symptom_without_permissions(self):
        user = self.create_user()
        role = self.create_role_with_permissions(permissions=[])

        facility = self.create_facility(user=user)
        organization = self.create_facility_organization(facility=facility)
        self.attach_role_facility_organization_user(organization, user, role)
        self.encounter = self.create_encounter(
            patient=self.patient, facility=facility, organization=organization
        )

        self.client.force_authenticate(user=user)
        symptom_data = self.generate_symptom_data(
            encounter_id=self.encounter.external_id
        )
        response = self.client.post(
            self.base_url, symptom_data.model_dump(mode="json"), format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_create_symptom_with_permissions(self):
        user = self.create_user()
        role = self.create_role_with_permissions(
            permissions=[EncounterPermissions.can_write_encounter.name],
        )

        facility = self.create_facility(user=user)
        organization = self.create_facility_organization(facility=facility)
        self.attach_role_facility_organization_user(organization, user, role)
        self.encounter = self.create_encounter(
            patient=self.patient, facility=facility, organization=organization
        )

        self.client.force_authenticate(user=user)
        symptom_data = self.generate_symptom_data(
            encounter_id=self.encounter.external_id
        )
        response = self.client.post(
            self.base_url, symptom_data.model_dump(mode="json"), format="json"
        )
        self.assertEqual(response.status_code, 200)

    def test_create_symptom_with_permissions_and_encounter_status_completed(self):
        user = self.create_user()
        role = self.create_role_with_permissions(
            permissions=[EncounterPermissions.can_write_encounter.name],
        )

        facility = self.create_facility(user=user)
        organization = self.create_facility_organization(facility=facility)
        self.attach_role_facility_organization_user(organization, user, role)
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=facility,
            organization=organization,
            status=StatusChoices.completed.value,
        )

        self.client.force_authenticate(user=user)
        symptom_data = self.generate_symptom_data(
            encounter_id=self.encounter.external_id
        )
        response = self.client.post(
            self.base_url, symptom_data.model_dump(mode="json"), format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_retrieve_symptom_with_permissions(self):
        user = self.create_user()
        role = self.create_role_with_permissions(
            permissions=[
                PatientPermissions.can_view_clinical_data.name,
                EncounterPermissions.can_write_encounter.name,
            ],
        )

        facility = self.create_facility(user=user)
        organization = self.create_facility_organization(facility=facility)
        self.attach_role_facility_organization_user(organization, user, role)
        self.encounter = self.create_encounter(
            patient=self.patient, facility=facility, organization=organization
        )

        self.client.force_authenticate(user=user)
        symptom_data = self.generate_symptom_data(
            encounter_id=self.encounter.external_id
        )
        response = self.client.post(
            self.base_url, symptom_data.model_dump(mode="json"), format="json"
        )
        self.assertEqual(response.status_code, 200)

        url = reverse(
            "symptom-detail",
            kwargs={
                "patient_external_id": self.patient.external_id,
                "external_id": response.json()["id"],
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(response.json()["id"]))

    def test_retrieve_symptom_without_permissions(self):
        user = self.create_user()
        role = self.create_role_with_permissions(
            permissions=[
                EncounterPermissions.can_write_encounter.name,
            ],
        )

        facility = self.create_facility(user=user)
        organization = self.create_facility_organization(facility=facility)
        self.attach_role_facility_organization_user(organization, user, role)
        self.encounter = self.create_encounter(
            patient=self.patient, facility=facility, organization=organization
        )

        self.client.force_authenticate(user=user)
        symptom_data = self.generate_symptom_data(
            encounter_id=self.encounter.external_id
        )
        response = self.client.post(
            self.base_url, symptom_data.model_dump(mode="json"), format="json"
        )
        self.assertEqual(response.status_code, 200)

        url = reverse(
            "symptom-detail",
            kwargs={
                "patient_external_id": self.patient.external_id,
                "external_id": response.json()["id"],
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
