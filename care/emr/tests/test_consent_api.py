import uuid
from datetime import timedelta
from secrets import choice

from django.forms import model_to_dict
from django.test import ignore_warnings
from django.urls import reverse
from model_bakery import baker

from care.emr.models.consent import Consent
from care.emr.resources.consent.spec import (
    CategoryChoice,
    ConsentStatusChoices,
    DecisionType,
)
from care.security.permissions.encounter import EncounterPermissions
from care.security.permissions.patient import PatientPermissions
from care.utils.tests.base import CareAPITestBase


@ignore_warnings(category=RuntimeWarning, message=r".*received a naive datetime.*")
class TestConsentViewSet(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.patient = self.create_patient()
        self.client.force_authenticate(user=self.user)

        self.base_url = reverse(
            "consent-list", kwargs={"patient_external_id": self.patient.external_id}
        )

    def _get_consent_url(self, consent_id):
        return reverse(
            "consent-detail",
            kwargs={
                "patient_external_id": self.patient.external_id,
                "external_id": consent_id,
            },
        )

    def create_consent(self, encounter, **kwargs):
        data = self.generate_data_for_consent(encounter, **kwargs)
        data.pop("encounter")
        return baker.make(Consent, encounter=encounter, **data)

    def generate_data_for_consent(self, encounter, **kwargs):
        start = self.fake.date_time_this_year()
        end = start + timedelta(days=1)

        data = {
            "encounter": encounter.external_id,
            "status": choice(list(ConsentStatusChoices)).value,
            "category": choice(list(CategoryChoice)).value,
            "date": self.fake.date_time_this_year().isoformat(),
            "decision": choice(list(DecisionType)).value,
            "period": {"start": start.isoformat(), "end": end.isoformat()},
        }
        data.update(**kwargs)
        return data

    # LIST TESTS
    def test_list_consent_with_permissions(self):
        permissions = [PatientPermissions.can_view_clinical_data.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        self.create_encounter(
            patient=self.patient, facility=self.facility, organization=self.organization
        )

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)

    def test_list_consent_without_permissions(self):
        self.create_encounter(
            patient=self.patient, facility=self.facility, organization=self.organization
        )
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 403)

    # RETRIEVE TESTS
    def test_retrieve_consent_with_permissions(self):
        permissions = [PatientPermissions.can_view_clinical_data.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        encounter = self.create_encounter(
            patient=self.patient, facility=self.facility, organization=self.organization
        )
        consent = self.create_consent(encounter=encounter)

        url = self._get_consent_url(consent.external_id)
        retrieve_response = self.client.get(url)
        self.assertEqual(retrieve_response.status_code, 200)

    def test_retrieve_consent_without_permissions(self):
        encounter = self.create_encounter(
            patient=self.patient, facility=self.facility, organization=self.organization
        )
        consent = self.create_consent(encounter=encounter)

        url = self._get_consent_url(consent.external_id)
        retrieve_response = self.client.get(url)
        self.assertEqual(retrieve_response.status_code, 403)

    # UPDATE TESTS
    def test_update_consent_with_permissions(self):
        permissions = [PatientPermissions.can_view_clinical_data.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        encounter = self.create_encounter(
            patient=self.patient, facility=self.facility, organization=self.organization
        )
        consent = self.create_consent(encounter=encounter)

        url = self._get_consent_url(consent.external_id)
        consent_data_updated = self.generate_data_for_consent(encounter)
        response = self.client.put(url, consent_data_updated, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["date"], consent_data_updated["date"])

    def test_update_consent_without_permissions(self):
        encounter = self.create_encounter(
            patient=self.patient, facility=self.facility, organization=self.organization
        )
        consent = self.create_consent(encounter=encounter)

        url = self._get_consent_url(consent.external_id)
        consent_data_updated = model_to_dict(consent)
        response = self.client.put(url, consent_data_updated, format="json")
        self.assertEqual(response.status_code, 403)

    # DELETE TESTS
    def test_delete_consent_with_permissions(self):
        permissions = [PatientPermissions.can_view_clinical_data.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        encounter = self.create_encounter(
            patient=self.patient, facility=self.facility, organization=self.organization
        )
        consent = self.create_consent(encounter=encounter)

        url = self._get_consent_url(consent.external_id)
        delete_response = self.client.delete(url, {}, format="json")
        self.assertEqual(delete_response.status_code, 204)

    def test_delete_consent_without_permissions(self):
        encounter = self.create_encounter(
            patient=self.patient, facility=self.facility, organization=self.organization
        )
        consent = self.create_consent(encounter=encounter)

        url = self._get_consent_url(consent.external_id)
        delete_response = self.client.delete(url, {}, format="json")
        self.assertEqual(delete_response.status_code, 403)

    def test_add_verification(self):
        permissions = [
            PatientPermissions.can_view_clinical_data.name,
            EncounterPermissions.can_write_encounter.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        encounter = self.create_encounter(
            patient=self.patient, facility=self.facility, organization=self.organization
        )
        consent = self.create_consent(encounter=encounter)

        url = f"{self._get_consent_url(consent.external_id)}add_verification/"
        data = {"verified": True, "verification_type": "validation"}

        # First verification attempt
        self.assertEqual(self.client.post(url, data, format="json").status_code, 200)

        # Duplicate verification attempt
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 400)
        error = response.json()["errors"][0]
        self.assertEqual(error["type"], "validation_error")
        self.assertIn("Consent is already verified by the user", error["msg"])

        # Verification by another user
        user_2 = self.create_user()
        self.client.force_authenticate(user_2)
        self.attach_role_facility_organization_user(self.organization, user_2, role)
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["verification_details"]), 2)

    def test_remove_verification(self):
        permissions = [
            PatientPermissions.can_view_clinical_data.name,
            EncounterPermissions.can_write_encounter.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        encounter = self.create_encounter(
            patient=self.patient, facility=self.facility, organization=self.organization
        )
        consent = self.create_consent(encounter=encounter)

        url = self._get_consent_url(consent.external_id)
        add_verification_url = f"{url}add_verification/"
        remove_verification_url = f"{url}remove_verification/"

        data = {"verified": True, "verification_type": "validation"}

        # Adding verification
        self.assertEqual(
            self.client.post(add_verification_url, data, format="json").status_code, 200
        )

        # Attempting to remove verification with a random UUID
        response = self.client.post(
            remove_verification_url, {"verified_by": uuid.uuid4()}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        error = response.json()["errors"][0]
        self.assertEqual(error["type"], "validation_error")
        self.assertIn("Consent is not verified by the user", error["msg"])

        # Removing verification by the actual user
        response = self.client.post(
            remove_verification_url,
            {"verified_by": self.user.external_id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["verification_details"]), 0)

    def test_for_attachments(self):
        permissions = [
            PatientPermissions.can_view_clinical_data.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        encounter = self.create_encounter(
            patient=self.patient, facility=self.facility, organization=self.organization
        )
        consent = self.create_consent(encounter=encounter)

        file_url = reverse("files-list")
        file_data = {
            "name": "Test Document",
            "file_type": "consent",
            "file_category": "consent_attachment",
            "original_name": "abcde.jpeg",
            "associating_id": consent.external_id,
        }
        response = self.client.post(file_url, file_data, format="json")
        self.assertEqual(response.status_code, 403)

        permissions = [
            EncounterPermissions.can_write_encounter.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        response = self.client.post(file_url, file_data, format="json")
        self.assertEqual(response.status_code, 200)

        consent_url = self._get_consent_url(consent.external_id)
        response = self.client.get(consent_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["source_attachments"]), 1)
