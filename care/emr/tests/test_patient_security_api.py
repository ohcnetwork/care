from django.urls import reverse
from rest_framework import status

from care.emr.models.patient import PatientIdentifier, PatientIdentifierConfig
from care.security.permissions.patient import PatientPermissions
from care.utils.tests.base import CareAPITestBase


class TestPatientSecurityAPI(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility_a = self.create_facility(self.user)
        self.facility_b = self.create_facility(self.user)

        self.org_a = self.create_organization(org_type="govt")

        # User has access to Facility A
        self.role = self.create_role_with_permissions(
            permissions=[
    PatientPermissions.can_write_facility_patient_identifier_config.name,
    PatientPermissions.can_write_patient.name,
    PatientPermissions.can_list_patients.name,
    ]
        )
        self.attach_role_organization_user(self.org_a, self.user, self.role)

        # Create a patient and link to Org A
        self.patient = self.create_patient(geo_organization=self.org_a)

    def test_update_identifier_bola_vulnerability(self):
        """
        Verify that a user cannot update an identifier using a config from another facility (BOLA).
        """
        # Create Identifier Config for Facility B
        config_b = PatientIdentifierConfig.objects.create(
            facility=self.facility_b,
            status="active",
            config={"required": True, "auto_maintained": False}
        )

        self.client.force_authenticate(user=self.user)
        url = reverse("patient-update-identifier", kwargs={"external_id": self.patient.external_id})

        payload = {
            "config": str(config_b.external_id),
            "value": "VULNERABLE_VALUE"
        }

        response = self.client.post(url, payload, format="json")

        # Verify that access is now blocked (403 Forbidden)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Verify the identifier was NOT created in the database
        exists = PatientIdentifier.objects.filter(
            patient=self.patient,
            config=config_b,
            value="VULNERABLE_VALUE"
        ).exists()
        self.assertFalse(exists, "Identifier was created despite 403 Forbidden")
