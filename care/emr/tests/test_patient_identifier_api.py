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

    def generate_patient_identifier_config_data(
        self, status=None, config=None, **kwargs
    ):
        return {
            "status": status or PatientIdentifierStatus.active,
            "config": config or self.generate_config(),
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

    # Test cases for patient identifier config retrieval

    def test_retrieve_patient_identifier_config_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        config = self.create_patient_identifier_config()
        response = self.client.get(
            self.get_detail_url(config.external_id), format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(config.external_id))

    def test_retrieve_patient_identifier_config_as_user_with_permission(self):
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)
        config = self.create_patient_identifier_config()
        response = self.client.get(
            self.get_detail_url(config.external_id), format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(config.external_id))

    def test_retrieve_patient_identifier_config_as_user_without_permission(self):
        self.client.force_authenticate(user=self.user)
        config = self.create_patient_identifier_config()
        response = self.client.get(
            self.get_detail_url(config.external_id), format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(config.external_id))

    def test_retrieve_patient_identifier_config_with_facility_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        config = self.create_patient_identifier_config(facility=self.facility)
        response = self.client.get(
            self.get_detail_url(config.external_id), format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(config.external_id))

    def test_retrieve_patient_identifier_config_with_facility_user_with_permission(
        self,
    ):
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)
        config = self.create_patient_identifier_config(facility=self.facility)
        response = self.client.get(
            self.get_detail_url(config.external_id), format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(config.external_id))

    def test_retrieve_patient_identifier_config_with_facility_user_without_permission(
        self,
    ):
        self.client.force_authenticate(user=self.user)
        config = self.create_patient_identifier_config(facility=self.facility)
        response = self.client.get(
            self.get_detail_url(config.external_id), format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "You do not have permission to read patient identifier configs",
            status_code=403,
        )

    def test_retrieve_patient_identifier_config_with_non_existent_id(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.get_detail_url("non-existent-id"), format="json"
        )
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Object not found", status_code=404)

    # Test cases for patient identifier config update

    def test_update_patient_identifier_config_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        config = self.generate_config(
            use=PatientIdentifierUse.official,
            system="http://example.com/official-identifier",
        )
        patient_identifier = self.create_patient_identifier_config()
        data = self.generate_patient_identifier_config_data(
            status=PatientIdentifierStatus.inactive, config=config
        )
        response = self.client.put(
            self.get_detail_url(patient_identifier.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(response.data["id"]), format="json"
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(
            get_response.data["status"], PatientIdentifierStatus.inactive.value
        )
        self.assertEqual(
            get_response.data["config"]["use"], PatientIdentifierUse.official.value
        )
        self.assertEqual(
            get_response.data["config"]["system"],
            "http://example.com/official-identifier",
        )

    def test_update_patient_identifier_config_as_user_with_permission(self):
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)
        patient_identifier = self.create_patient_identifier_config()
        data = self.generate_patient_identifier_config_data(
            status=PatientIdentifierStatus.inactive
        )
        response = self.client.put(
            self.get_detail_url(patient_identifier.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"],
            "You are not authorized to update a patient identifier config",
        )

    def test_update_patient_identifier_config_with_facility_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        config = self.generate_config(
            use=PatientIdentifierUse.official,
            system="http://example.com/official-identifier",
        )
        patient_identifier = self.create_patient_identifier_config(
            facility=self.facility
        )
        data = self.generate_patient_identifier_config_data(
            status=PatientIdentifierStatus.inactive, config=config
        )
        response = self.client.put(
            self.get_detail_url(patient_identifier.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(response.data["id"]), format="json"
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(
            get_response.data["status"], PatientIdentifierStatus.inactive.value
        )
        self.assertEqual(
            get_response.data["config"]["use"], PatientIdentifierUse.official.value
        )
        self.assertEqual(
            get_response.data["config"]["system"],
            "http://example.com/official-identifier",
        )

    def test_update_patient_identifier_config_with_facility_user_with_permission(self):
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)
        patient_identifier = self.create_patient_identifier_config(
            facility=self.facility
        )
        data = self.generate_patient_identifier_config_data(
            status=PatientIdentifierStatus.inactive
        )
        response = self.client.put(
            self.get_detail_url(patient_identifier.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(response.data["id"]), format="json"
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(
            get_response.data["status"], PatientIdentifierStatus.inactive.value
        )
        self.assertEqual(
            get_response.data["config"]["use"], PatientIdentifierUse.usual.value
        )
        self.assertEqual(
            get_response.data["config"]["system"], "http://example.com/identifier"
        )

    def test_update_patient_identifier_config_with_facility_user_without_permission(
        self,
    ):
        self.client.force_authenticate(user=self.user)
        patient_identifier = self.create_patient_identifier_config(
            facility=self.facility
        )
        data = self.generate_patient_identifier_config_data(
            status=PatientIdentifierStatus.inactive
        )
        response = self.client.put(
            self.get_detail_url(patient_identifier.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "You do not have permission to write patient identifier configs",
            status_code=403,
        )

    def test_update_patient_identifier_config_with_duplicate_system(self):
        self.client.force_authenticate(user=self.superuser)
        config = self.generate_config(system="http://example.com/official-identifier")
        self.create_patient_identifier_config()
        patient_identifier = self.create_patient_identifier_config(config=config)
        data = self.generate_patient_identifier_config_data()
        response = self.client.put(
            self.get_detail_url(patient_identifier.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "A patient identifier config with this system already exists",
            status_code=400,
        )

    def test_update_patient_identifier_config_with_duplicate_system_in_facility(self):
        self.client.force_authenticate(user=self.superuser)
        config = self.generate_config(system="http://example.com/official-identifier")
        self.create_patient_identifier_config(facility=self.facility)
        patient_identifier = self.create_patient_identifier_config(
            facility=self.facility, config=config
        )
        data = self.generate_patient_identifier_config_data(
            facility=self.facility.external_id
        )
        response = self.client.put(
            self.get_detail_url(patient_identifier.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "A patient identifier config with this system already exists",
            status_code=400,
        )

    def test_update_patient_identifier_config_with_duplicate_system_as_user_with_permission(
        self,
    ):
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)
        config = self.generate_config(system="http://example.com/official-identifier")
        self.create_patient_identifier_config()
        patient_identifier = self.create_patient_identifier_config(config=config)
        data = self.generate_patient_identifier_config_data()
        response = self.client.put(
            self.get_detail_url(patient_identifier.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "A patient identifier config with this system already exists",
            status_code=400,
        )

    def test_update_patient_identifier_config_with_duplicate_system_in_facility_as_user_with_permission(
        self,
    ):
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)
        config = self.generate_config(system="http://example.com/official-identifier")
        self.create_patient_identifier_config(facility=self.facility)
        patient_identifier = self.create_patient_identifier_config(
            facility=self.facility, config=config
        )
        data = self.generate_patient_identifier_config_data(
            facility=self.facility.external_id
        )
        response = self.client.put(
            self.get_detail_url(patient_identifier.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "A patient identifier config with this system already exists",
            status_code=400,
        )

        # Test cases for patient identifier config lists

    def test_list_patient_identifier_configs_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        config = self.create_patient_identifier_config()
        self.create_patient_identifier_config(facility=self.facility)
        response = self.client.get(self.base_url, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], str(config.external_id))

    def test_list_patient_identifier_configs_as_user(self):
        self.client.force_authenticate(user=self.user)
        config = self.create_patient_identifier_config()
        self.create_patient_identifier_config(facility=self.facility)
        response = self.client.get(self.base_url, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], str(config.external_id))

    def test_list_patient_identifier_configs_with_facility_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        config = self.generate_config(
            use=PatientIdentifierUse.official,
            system="http://example.com/official-identifier",
        )
        self.create_patient_identifier_config()
        patient_identifier1 = self.create_patient_identifier_config(
            facility=self.facility
        )
        patient_identifier2 = self.create_patient_identifier_config(
            facility=self.facility, config=config
        )

        response = self.client.get(
            self.base_url, {"facility": self.facility.external_id}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(
            response.data["results"][0]["id"], str(patient_identifier2.external_id)
        )
        self.assertEqual(
            response.data["results"][1]["id"], str(patient_identifier1.external_id)
        )

    def test_list_patient_identifier_configs_with_facility_user_with_permission(self):
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)
        config = self.generate_config(
            use=PatientIdentifierUse.official,
            system="http://example.com/official-identifier",
        )
        self.create_patient_identifier_config()
        patient_identifier1 = self.create_patient_identifier_config(
            facility=self.facility
        )
        patient_identifier2 = self.create_patient_identifier_config(
            facility=self.facility, config=config
        )

        response = self.client.get(
            self.base_url, {"facility": self.facility.external_id}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(
            response.data["results"][0]["id"], str(patient_identifier2.external_id)
        )
        self.assertEqual(
            response.data["results"][1]["id"], str(patient_identifier1.external_id)
        )

    def test_list_patient_identifier_configs_with_facility_user_without_permission(
        self,
    ):
        self.client.force_authenticate(user=self.user)
        config = self.generate_config(
            use=PatientIdentifierUse.official,
            system="http://example.com/official-identifier",
        )
        self.create_patient_identifier_config()
        self.create_patient_identifier_config(facility=self.facility)
        self.create_patient_identifier_config(facility=self.facility, config=config)

        response = self.client.get(
            self.base_url, {"facility": self.facility.external_id}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "You do not have permission to read patient identifier configs",
            status_code=403,
        )
