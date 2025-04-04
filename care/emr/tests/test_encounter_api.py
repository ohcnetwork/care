from django.urls import reverse

from care.security.permissions.encounter import EncounterPermissions
from care.security.permissions.patient import PatientPermissions
from care.utils.tests.base import CareAPITestBase


class EncouterFilterTests(CareAPITestBase):
    """
    Foundation test class that provides common setup and helper methods for testing questionnaire functionality.

    This class handles the initial setup of test data including users, organizations, and patients,
    as well as providing utility methods for questionnaire submission and validation.
    """

    def setUp(self):
        self.user = self.create_super_user()
        self.organization = self.create_organization(org_type="govt")
        self.facility = self.create_facility(self.user)
        self.facility_organization = self.create_facility_organization(self.facility)
        self.patient = self.create_patient()
        self.client.force_authenticate(user=self.user)

        self.base_url = reverse("encounter-list")

    def _create_encounter(self, **kwargs):
        """
        Helper method to create an encounter with the given parameters.
        """
        url = reverse("encounter-list")
        data = {
            "status": "planned",
            "encounter_class": "amb",
            "priority": "routine",
            "patient": self.patient.external_id,
            "facility": self.facility.external_id,
            "organization": [self.facility_organization.external_id],
        }
        data.update(kwargs)
        response = self.client.post(url, data=data, format="json")
        self.assertEqual(
            response.status_code, 200, f"Encounter creation failed: {response.json()}"
        )
        return response

    def test_filter_by_identifiers(self):
        """
        Test filtering encounters by identifiers.
        """
        permissions = [
            PatientPermissions.can_view_clinical_data.name,
            EncounterPermissions.can_list_encounter.name,
            EncounterPermissions.can_read_encounter.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, role
        )

        self._create_encounter(
            external_identifier="12345",
        )
        patient2 = self.create_patient()
        self._create_encounter(
            external_identifier="67890",
            patient=str(patient2.external_id),
        )

        response = self.client.get(
            self.base_url,
            {
                "facility": self.facility.external_id,
                "identifier_value": "12345",
                "identifier_type": "MR",
            },
            format="json",
        )
        self.assertEqual(
            response.status_code, 200, f"Request failed: {response.json()}"
        )
        self.assertEqual(
            len(response.data["results"]),
            1,
            f"Should return one encounter, got {len(response.data["results"])}",
        )
        self.assertEqual(
            response.data["results"][0]["external_identifier"],
            "12345",
            "Should match identifier",
        )
