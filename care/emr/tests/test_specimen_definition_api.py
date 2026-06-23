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
            "slug_value": "test-definition",
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

    def get_detail_url(self, slug):
        return reverse(
            "specimen_definition-detail",
            kwargs={"facility_external_id": self.facility.external_id, "slug": slug},
        )

    def create_specimen_definition(self, slug=None, **kwargs):
        return baker.make(
            "emr.SpecimenDefinition",
            facility=self.facility,
            slug=f"f-{self.facility.external_id}-{slug}",
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
        """Test creating a specimen definition as a superuser."""
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.base_url, self.specimen_definition_data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_detail_url(response.data["slug"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_specimen_definition_as_user_with_permission(self):
        """Test creating a specimen definition as a user with permission."""
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
        get_response = self.client.get(self.get_detail_url(response.data["slug"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_specimen_definition_without_permission(self):
        """Test creating a specimen definition without permission."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.base_url, self.specimen_definition_data, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "Access Denied to Specimen Definition", status_code=403
        )

    def test_create_specimen_definition_with_same_slug(self):
        """Test creating a specimen definition with the same slug."""
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        self.create_specimen_definition(
            slug=self.specimen_definition_data["slug_value"],
            title="test-specimen-definition",
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

    def test_create_specimen_definition_with_invalid_data(self):
        """Test creating a specimen definition with invalid data with minimum_volume specification should only contain quantity or string."""
        self.client.force_authenticate(user=self.superuser)
        invalid_data = self.specimen_definition_data.copy()
        invalid_data["type_tested"] = {
            "is_derived": False,
            "preference": "preferred",
            "container": {
                "minimum_volume": {
                    "quantity": {
                        "value": 5.00,
                        "unit": {"code": "mL", "system": "http://unitsofmeasure.org"},
                    },
                    "string": "Five milliliters",
                }
            },
        }
        response = self.client.post(self.base_url, invalid_data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Only one of quantity or string should be provided", str(response.data)
        )

    # Test for retrieving a specimen definition

    def test_retrieve_specimen_definition_as_super_user(self):
        """Test retrieving a specimen definition as a superuser."""
        specimen_definition = self.create_specimen_definition(
            slug="test-specimen-definition", title="Test Specimen Definition"
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.get_detail_url(specimen_definition.slug))
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
        response = self.client.get(self.get_detail_url(specimen_definition.slug))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(specimen_definition.external_id))

    def test_retrieve_specimen_definition_without_permission(self):
        """Test retrieving a specimen definition without permission."""
        specimen_definition = self.create_specimen_definition(
            slug="s-definition", title="Test Specimen Definition"
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.get_detail_url(specimen_definition.slug))
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "Access Denied to Specimen Definition", status_code=403
        )

    def test_retrieve_non_existent_specimen_definition(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.get_detail_url("non-existent-id"))
        self.assertEqual(response.status_code, 404)
        self.assertContains(
            response, "No SpecimenDefinition matches the given query.", status_code=404
        )

    # Test for updating a specimen definition

    def test_update_specimen_definition_as_super_user(self):
        """Test updating a specimen definition as a superuser."""
        specimen_definition = self.create_specimen_definition(
            slug="test-specimen-definition", title="Test Specimen Definition"
        )
        self.client.force_authenticate(user=self.superuser)
        update_data = self.specimen_definition_data.copy()
        update_data["title"] = "Updated Test Specimen Definition"
        update_data["slug_value"] = "updated-s-definition"
        update_data["status"] = SpecimenDefinitionStatusOptions.retired
        update_data["type_collected"] = {
            "code": "urine",
            "display": "Urine",
        }
        response = self.client.put(
            self.get_detail_url(specimen_definition.slug),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_detail_url(response.data["slug"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["title"], update_data["title"])
        self.assertEqual(
            get_response.data["slug_config"]["slug_value"], update_data["slug_value"]
        )
        self.assertEqual(get_response.data["status"], update_data["status"])
        self.assertEqual(
            get_response.data["type_collected"], update_data["type_collected"]
        )

    def test_update_specimen_definition_as_user_with_permission(self):
        """Test updating a specimen definition as a user with permission."""
        specimen_definition = self.create_specimen_definition(
            slug="test-s-definition", title="Test Specimen Definition"
        )
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)
        update_data = self.specimen_definition_data.copy()
        update_data["title"] = "Updated Test Specimen Definition"
        update_data["slug_value"] = "updated-t-definition"
        update_data["status"] = SpecimenDefinitionStatusOptions.retired
        update_data["type_collected"] = {
            "code": "urine",
            "display": "Urine",
        }
        response = self.client.put(
            self.get_detail_url(specimen_definition.slug),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_detail_url(response.data["slug"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["title"], update_data["title"])
        self.assertEqual(
            get_response.data["slug_config"]["slug_value"], update_data["slug_value"]
        )
        self.assertEqual(get_response.data["status"], update_data["status"])
        self.assertEqual(
            get_response.data["type_collected"], update_data["type_collected"]
        )

    def test_update_specimen_definition_without_permission(self):
        """Test updating a specimen definition without permission."""
        specimen_definition = self.create_specimen_definition(
            slug="test-specimen-definition", title="Test Specimen Definition"
        )
        self.client.force_authenticate(user=self.user)
        update_data = self.specimen_definition_data.copy()
        update_data["title"] = "Updated Test Specimen Definition"
        update_data["slug_value"] = "updated-test-specimen-definition"
        update_data["status"] = SpecimenDefinitionStatusOptions.retired
        update_data["type_collected"] = {
            "code": "urine",
            "display": "Urine",
        }
        response = self.client.put(
            self.get_detail_url(specimen_definition.slug),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "Access Denied to Specimen Definition", status_code=403
        )

    # Test for listing specimen definitions

    def test_list_specimen_definitions_as_super_user(self):
        """Test listing specimen definitions as a superuser."""
        self.client.force_authenticate(user=self.superuser)
        self.create_specimen_definition(
            slug="test-specimen-definition", title="Test Specimen Definition"
        )
        self.create_specimen_definition(
            slug="test-specimen-definition-2", title="Test Specimen Definition 2"
        )
        response = self.client.get(self.base_url, format="json")
        self.assertEqual(response.status_code, 200)

    def test_list_specimen_definitions_as_user_with_permission(self):
        """Test listing specimen definitions as a user with permission."""
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)
        self.create_specimen_definition(
            slug="test-specimen-definition", title="Test Specimen Definition"
        )
        self.create_specimen_definition(
            slug="test-specimen-definition-2", title="Test Specimen Definition 2"
        )
        response = self.client.get(self.base_url, format="json")
        self.assertEqual(response.status_code, 200)

    def test_list_specimen_definitions_without_permission(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.base_url, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "Access Denied to Specimen Definition", status_code=403
        )

    # Test for filtering specimen definitions

    def test_filter_specimen_definitions_by_title(self):
        """Test filtering specimen definitions by title."""
        self.client.force_authenticate(user=self.superuser)
        self.create_specimen_definition(
            slug="test-specimen-definition",
            title="Test Specimen Definition",
        )
        self.create_specimen_definition(
            slug="test-specimen-definition-2", title="Test Sample Definition"
        )
        response = self.client.get(
            self.base_url, {"title": "Test Specimen Definition"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["title"], "Test Specimen Definition"
        )

    def test_filter_specimen_definitions_by_status(self):
        """Test filtering specimen definitions by status."""
        self.client.force_authenticate(user=self.superuser)
        self.create_specimen_definition(
            slug="test-specimen-definition",
            title="Test Specimen Definition",
        )
        self.create_specimen_definition(
            slug="test-specimen-definition-2",
            title="Test Sample Definition",
        )
        response = self.client.get(self.base_url, {"status": "active"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        for result in response.data["results"]:
            self.assertEqual(result["status"], "active")
