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

    def create_specimen_definition(self, **kwargs):
        return baker.make(
            "emr.SpecimenDefinition",
            facility=self.facility,
            status=SpecimenDefinitionStatusOptions.active,
            description="This is a test specimen definition.",
            type_collected={"code": "blood", "display": "Blood"},
            patient_preparation=[{"code": "fasting", "display": "Fasting"}],
            collection={"code": "venipuncture", "display": "Venipuncture"},
            type_tested={"code": "cbc", "display": "Complete Blood Count"},
            **kwargs,
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
        self.create_specimen_definition(
            slug=self.specimen_definition_data["slug"], title="test-specimen-definition"
        )
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

    # Test for retrieving a specimen definition

    def test_retrieve_specimen_definition_as_super_user(self):
        specimen_definition = self.create_specimen_definition(
            slug="test-specimen-definition", title="Test Specimen Definition"
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.get_detail_url(specimen_definition.external_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(specimen_definition.external_id))

    def test_retrieve_specimen_definition_as_user_with_permission(self):
        specimen_definition = self.create_specimen_definition(
            slug="test-specimen-definition", title="Test Specimen Definition"
        )
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.get_detail_url(specimen_definition.external_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(specimen_definition.external_id))

    def test_retrieve_specimen_definition_without_permission(self):
        specimen_definition = self.create_specimen_definition(
            slug="test-specimen-definition", title="Test Specimen Definition"
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.get_detail_url(specimen_definition.external_id))
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "Access Denied to Specimen Definition", status_code=403
        )

    def test_retrieve_non_existent_specimen_definition(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.get_detail_url("non-existent-id"))
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Object not found", status_code=404)

    # Test for updating a specimen definition

    def test_update_specimen_definition_as_super_user(self):
        specimen_definition = self.create_specimen_definition(
            slug="test-specimen-definition", title="Test Specimen Definition"
        )
        self.client.force_authenticate(user=self.superuser)
        update_data = self.specimen_definition_data.copy()
        update_data["title"] = "Updated Test Specimen Definition"
        update_data["slug"] = "updated-test-specimen-definition"
        update_data["status"] = SpecimenDefinitionStatusOptions.retired
        update_data["type_collected"] = {
            "code": "urine",
            "display": "Urine",
        }
        response = self.client.put(
            self.get_detail_url(specimen_definition.external_id),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(specimen_definition.external_id)
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["title"], update_data["title"])
        self.assertEqual(get_response.data["slug"], update_data["slug"])
        self.assertEqual(get_response.data["status"], update_data["status"])
        self.assertEqual(
            get_response.data["type_collected"], update_data["type_collected"]
        )

    def test_update_specimen_definition_as_user_with_permission(self):
        specimen_definition = self.create_specimen_definition(
            slug="test-specimen-definition", title="Test Specimen Definition"
        )
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)
        update_data = self.specimen_definition_data.copy()
        update_data["title"] = "Updated Test Specimen Definition"
        update_data["slug"] = "updated-test-specimen-definition"
        update_data["status"] = SpecimenDefinitionStatusOptions.retired
        update_data["type_collected"] = {
            "code": "urine",
            "display": "Urine",
        }
        response = self.client.put(
            self.get_detail_url(specimen_definition.external_id),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(specimen_definition.external_id)
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["title"], update_data["title"])
        self.assertEqual(get_response.data["slug"], update_data["slug"])
        self.assertEqual(get_response.data["status"], update_data["status"])
        self.assertEqual(
            get_response.data["type_collected"], update_data["type_collected"]
        )

    def test_update_specimen_definition_without_permission(self):
        specimen_definition = self.create_specimen_definition(
            slug="test-specimen-definition", title="Test Specimen Definition"
        )
        self.client.force_authenticate(user=self.user)
        update_data = self.specimen_definition_data.copy()
        update_data["title"] = "Updated Test Specimen Definition"
        update_data["slug"] = "updated-test-specimen-definition"
        update_data["status"] = SpecimenDefinitionStatusOptions.retired
        update_data["type_collected"] = {
            "code": "urine",
            "display": "Urine",
        }
        response = self.client.put(
            self.get_detail_url(specimen_definition.external_id),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "Access Denied to Specimen Definition", status_code=403
        )
