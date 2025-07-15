from django.urls import reverse
from model_bakery import baker

from care.emr.resources.specimen_definition.spec import (
    PreferenceOptions,
    SpecimenDefinitionStatusOptions,
)
from care.security.permissions.specimen_definition import SpecimenDefinitionPermissions
from care.utils.tests.base import CareAPITestBase


class SpecimenDefinitionAPITest(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user(username="test-user")
        self.superuser = self.create_super_user(username="test-superuser")
        self.facility = self.create_facility(user=self.superuser, name="test-facility")
        self.facility_location = baker.make(
            "emr.FacilityLocation",
            facility=self.facility,
            name="test-facility-location",
        )
        self.facility_organization = self.create_facility_organization(
            name="test-facility-organization",
            facility=self.facility,
            org_type="root",
        )

        self.specimen_definition_data = {
            "slug": "test-specimen-definition",
            "title": "Test Specimen Definition",
            "status": SpecimenDefinitionStatusOptions.active,
            "description": "This is a test specimen definition.",
            "type_collected": {"code": "blood", "display": "Blood"},
            "patient_preparation": [{"code": "fasting", "display": "Fasting"}],
            "collection": {"code": "venipuncture", "display": "Venipuncture"},
            "type_tested": {
                "is_derived": False,
                "preference": PreferenceOptions.preferred,
                "container": None,
                "requirement": None,
                "retention_time": None,
                "single_use": None,
            },
        }

        self.base_url = reverse(
            "specimen_definition-list",
            kwargs={"facility_external_id": self.facility.external_id},
        )

        self.role = self.create_role_with_permissions(
            permissions=[
                SpecimenDefinitionPermissions.can_write_specimen_definition.name,
                SpecimenDefinitionPermissions.can_read_specimen_definition.name,
            ],
        )

    def get_detail_url(self, external_id):
        return reverse(
            "specimen_definition-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": external_id,
            },
        )

    def create_specimen_definition(self):
        return baker.make(
            "emr.SpecimenDefinition",
            facility=self.facility,
            slug="test-specimen-definition",
            title="Test Specimen Definition",
            status=SpecimenDefinitionStatusOptions.active,
            description="This is a test specimen definition.",
            type_collected={"code": "blood", "display": "Blood"},
            patient_preparation=[{"code": "fasting", "display": "Fasting"}],
            collection={"code": "venipuncture", "display": "Venipuncture"},
            type_tested={"code": "cbc", "display": "Complete Blood Count"},
        )

    # Test for creating a specimen definition

    def test_create_specimen_definition_as_super_user(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.base_url, self.specimen_definition_data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_detail_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_specimen_definition_as_user_with_permission(self):
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.base_url, self.specimen_definition_data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_detail_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_specimen_definition_without_permission(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.base_url, self.specimen_definition_data, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "Access Denied to Specimen Definition", status_code=403
        )

    def test_create_specimen_definition_with_same_slug(self):
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        self.create_specimen_definition()
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.base_url, self.specimen_definition_data, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Specimen Definition with this slug already exists.",
            status_code=400,
        )
