from django.urls import reverse
from model_bakery import baker

from care.emr.resources.patient_identifier.spec import (
    PatientIdentifierStatus,
    PatientIdentifierUse,
)
from care.security.permissions.patient_identifier_config import (
    PatientIdentifierConfigPermissions,
)
from care.utils.tests.base import CareAPITestBase


class TestPatientIdentifierConfigAPI(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user(username="testuser")
        self.superuser = self.create_super_user(username="testsuperuser")
        self.facility = self.create_facility(name="Test Facility", user=self.superuser)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility, name="Test Facility Org", org_type="root"
        )
        self.base_url = reverse("patient-identifier-config-list")
        self.role = self.create_role_with_permissions(
            permissions=[
                PatientIdentifierConfigPermissions.can_read_patient_identifier_config.name,
                PatientIdentifierConfigPermissions.can_write_patient_identifier_config.name,
            ]
        )

    def generate_config(self, system=None, use=None):
        return {
            "use": use or PatientIdentifierUse.usual,
            "description": "Test Identifier Config",
            "system": system or "http://example.com/identifier",
            "required": True,
            "unique": True,
            "regex": r"^\d{3}-\d{2}-\d{4}$",
            "display": "Test Identifier Display",
            "retrieve_config": {
                "retrieve_with_dob": False,
                "retrieve_with_year_of_birth": False,
                "retrieve_with_otp": False,
            },
            "default_value": None,
        }

    def generate_patient_identifier_config_data(self, status=None, **kwargs):
        return {
            "status": status or PatientIdentifierStatus.active,
            "config": self.generate_config(),
            **kwargs,
        }

    def get_detail_url(self, external_id):
        return reverse(
            "patient-identifier-config-detail", kwargs={"external_id": external_id}
        )

    def create_patient_identifier_config(self, status=None, facility=None, config=None):
        patient_identifier_config_data = self.generate_patient_identifier_config_data(
            status=status, facility=facility, config=config
        )
        return baker.make(
            "emr.PatientIdentifierConfig", **patient_identifier_config_data
        )

    # Test cases for patient identifier config creation

    def test_create_patient_identifier_config_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        data = self.generate_patient_identifier_config_data()
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(response.data["id"]), format="json"
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_patient_identifier_config_as_user_with_permission(self):
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)
        data = self.generate_patient_identifier_config_data()
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"],
            "You are not authorized to create a patient identifier config",
        )

    def test_create_patient_identifier_config_with_facility_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.base_url,
            self.generate_patient_identifier_config_data(
                facility=self.facility.external_id
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(response.data["id"]), format="json"
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_patient_identifier_config_with_facility_user_with_permission(self):
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.base_url,
            self.generate_patient_identifier_config_data(
                facility=self.facility.external_id
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(response.data["id"]), format="json"
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_patient_identifier_config_with_facility_user_without_permission(
        self,
    ):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.base_url,
            self.generate_patient_identifier_config_data(
                facility=self.facility.external_id
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "You do not have permission to write patient identifier configs",
            status_code=403,
        )

    def test_create_patient_identifier_config_with_duplicate_system(self):
        self.client.force_authenticate(user=self.superuser)
        self.create_patient_identifier_config(config=self.generate_config())
        data = self.generate_patient_identifier_config_data()
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "A patient identifier config with this system already exists",
            status_code=400,
        )

    def test_create_patient_identifier_config_with_duplicate_system_in_facility(self):
        self.client.force_authenticate(user=self.superuser)
        self.create_patient_identifier_config(
            config=self.generate_config(), facility=self.facility
        )
        data = self.generate_patient_identifier_config_data(
            facility=self.facility.external_id
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "A patient identifier config with this system already exists",
            status_code=400,
        )

    def test_create_patient_identifier_config_with_duplicate_system_in_different_facility(
        self,
    ):
        self.client.force_authenticate(user=self.superuser)
        other_facility = self.create_facility(
            name="Other Facility", user=self.superuser
        )
        self.create_patient_identifier_config(
            config=self.generate_config(), facility=other_facility
        )
        data = self.generate_patient_identifier_config_data(
            facility=self.facility.external_id
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(response.data["id"]), format="json"
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_patient_identifier_config_with_duplicate_system_as_user_with_permission(
        self,
    ):
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)
        self.create_patient_identifier_config(config=self.generate_config())
        data = self.generate_patient_identifier_config_data()
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "A patient identifier config with this system already exists",
            status_code=400,
        )

    def test_create_patient_identifier_config_with_duplicate_system_in_facility_as_user_with_permission(
        self,
    ):
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)
        self.create_patient_identifier_config(
            config=self.generate_config(), facility=self.facility
        )
        data = self.generate_patient_identifier_config_data(
            facility=self.facility.external_id
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "A patient identifier config with this system already exists",
            status_code=400,
        )
