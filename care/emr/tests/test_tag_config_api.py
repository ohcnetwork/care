import uuid

from django.urls import reverse
from model_bakery import baker

from care.emr.resources.tag.config_spec import (
    TagCategoryChoices,
    TagResource,
    TagStatus,
)
from care.security.permissions.tag_config import TagConfigPermissions
from care.utils.tests.base import CareAPITestBase


class TestTagConfigAPI(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user(username="testuser")
        self.superuser = self.create_super_user(username="testsuperuser")
        self.facility = self.create_facility(name="Test Facility", user=self.superuser)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility, name="Test Facility Org", org_type="root"
        )
        self.organization = self.create_organization(
            name="Test Organization", user=self.superuser
        )
        self.base_url = reverse("tag_config-list")
        self.role = self.create_role_with_permissions(
            permissions=[
                TagConfigPermissions.can_read_tag_config.name,
                TagConfigPermissions.can_write_tag_config.name,
            ],
        )

    def generate_tag_config_data(
        self, status=None, category=None, resource=None, slug=None, **kwargs
    ):
        return {
            "status": status or TagStatus.active.value,
            "display": "Test Tag",
            "description": "This is a test tag config",
            "category": category or TagCategoryChoices.clinical.value,
            "priority": 1,
            "resource": resource or TagResource.encounter.value,
            **kwargs,
        }

    def get_detail_url(self, external_id):
        return reverse("tag_config-detail", kwargs={"external_id": external_id})

    def create_tag_config(self, status=None, category=None, resource=None, **kwargs):
        tag_config_data = self.generate_tag_config_data(
            **kwargs,
            status=status,
            category=category,
            resource=resource,
        )
        return baker.make("emr.TagConfig", **tag_config_data)

    # Test cases for create tagconfig

    def test_create_tag_config_with_organization_as_superuser(self):
        """Test creating a tag config with organization as superuser"""
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.base_url,
            self.generate_tag_config_data(organization=self.organization.external_id),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_detail_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)

    def test_create_tag_config_with_facility_as_superuser(self):
        """Test creating a tag config with facility as superuser"""
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.base_url,
            self.generate_tag_config_data(facility=self.facility.external_id),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_detail_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)

    def test_create_tag_config_global_as_superuser(self):
        """Test creating a global tag config as superuser"""
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.base_url, self.generate_tag_config_data(), format="json"
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_detail_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(response.data["id"], get_response.data["id"])

    def test_create_tag_config_with_only_facility_organization_as_superuser(self):
        """Test creating a tag config with only facility organization as superuser"""
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.base_url,
            self.generate_tag_config_data(
                facility_organization=self.facility_organization.external_id
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Facility Organization not allowed in instance level tag configs",
            status_code=400,
        )

    def test_create_tag_config_with_organization_as_user_with_permission(self):
        """Test creating a tag config with organization as user with permission"""
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.base_url,
            self.generate_tag_config_data(organization=self.organization.external_id),
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "You do not have permission to write tag configs", status_code=403
        )

    def test_create_tag_config_with_facility_as_user_with_permission(self):
        """Test creating a tag config with facility as user with permission"""
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(self.user)
        response = self.client.post(
            self.base_url,
            self.generate_tag_config_data(facility=self.facility.external_id),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_detail_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(response.data["id"], get_response.data["id"])

    def test_create_tag_config_with_facility_organization_as_user_with_permission(self):
        """Test creating a tag config with facility organization as user with permission"""
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(self.user)
        response = self.client.post(
            self.base_url,
            self.generate_tag_config_data(
                facility=self.facility.external_id,
                facility_organization=self.facility_organization.external_id,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_detail_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(response.data["id"], get_response.data["id"])

    def test_create_tag_config_as_user_without_permission(self):
        """Test creating a tag config as user without permission"""
        self.client.force_authenticate(self.user)
        response = self.client.post(
            self.base_url,
            self.generate_tag_config_data(
                facility=self.facility.external_id,
                facility_organization=self.facility_organization.external_id,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "You do not have permission to write tag configs", status_code=403
        )

    def test_create_tag_config_as_user_with_invalid_facility(self):
        """Test creating a tag config as user with invalid facility"""
        self.client.force_authenticate(self.user)
        invalid_facility = str(uuid.uuid4())
        response = self.client.post(
            self.base_url,
            self.generate_tag_config_data(facility=invalid_facility),
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertContains(
            response, "No Facility matches the given query.", status_code=404
        )

    def test_create_tag_config_as_user_with_invalid_facility_organization(self):
        """Test creating a tag config as user with invalid facility organization"""
        self.client.force_authenticate(self.user)
        response = self.client.post(
            self.base_url,
            self.generate_tag_config_data(
                facility=self.facility.external_id,
                facility_organization=str(uuid.uuid4()),
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response, "Facility Organization not found", status_code=400
        )

    def test_create_tag_config_as_user_with_invalid_organization(self):
        """Test creating a tag config as user with invalid organization"""
        self.client.force_authenticate(self.user)
        response = self.client.post(
            self.base_url,
            self.generate_tag_config_data(organization=str(uuid.uuid4())),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Organization not found", status_code=400)

    def test_create_tag_config_with_parent_with_same_resource_globally(self):
        """Test creating a tag config with parent with same resource globally"""
        self.client.force_authenticate(user=self.superuser)
        parent_tag = self.create_tag_config(
            resource=TagResource.encounter,
        )
        response = self.client.post(
            self.base_url,
            self.generate_tag_config_data(
                resource=TagResource.encounter,
                parent=parent_tag.external_id,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_detail_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(response.data["id"], get_response.data["id"])

    def test_create_tag_config_with_parent_with_different_resource_globally(self):
        """Test creating a tag config with parent with different resource globally"""
        self.client.force_authenticate(user=self.superuser)
        parent_tag = self.create_tag_config(
            resource=TagResource.encounter,
        )
        response = self.client.post(
            self.base_url,
            self.generate_tag_config_data(
                resource=TagResource.patient.value,
                parent=parent_tag.external_id,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Parent tag config not found", status_code=400)

    def test_create_tag_config_with_parent_with_same_resource_in_facility(self):
        """Test creating a tag config with parent with same resource in facility"""
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        parent_tag = self.create_tag_config(
            resource=TagResource.encounter,
            facility=self.facility,
        )
        response = self.client.post(
            self.base_url,
            self.generate_tag_config_data(
                resource=TagResource.encounter,
                parent=parent_tag.external_id,
                facility=self.facility.external_id,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_detail_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(response.data["id"], get_response.data["id"])

    def test_create_tag_config_with_parent_with_different_resource_in_facility(self):
        """Test creating a tag config with parent with different resource in facility"""
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        parent_tag = self.create_tag_config(
            resource=TagResource.encounter,
            facility=self.facility,
        )
        response = self.client.post(
            self.base_url,
            self.generate_tag_config_data(
                resource=TagResource.patient.value,
                parent=parent_tag.external_id,
                facility=self.facility.external_id,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Parent tag config not found", status_code=400)

    def test_create_tag_config_with_parent_with_same_resource_in_different_facility(
        self,
    ):
        """Test creating a tag config with parent with same resource in different facility"""
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        parent_tag = self.create_tag_config(
            resource=TagResource.encounter,
            facility=self.facility,
        )
        another_facility = self.create_facility(user=self.superuser)
        response = self.client.post(
            self.base_url,
            self.generate_tag_config_data(
                resource=TagResource.encounter,
                parent=parent_tag.external_id,
                facility=another_facility.external_id,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Parent tag config not found", status_code=400)

    def test_create_tag_config_with_parent_with_same_resource_in_organization(self):
        """Test creating a tag config with parent with same resource in organization"""
        self.client.force_authenticate(user=self.superuser)
        parent_tag = self.create_tag_config(
            resource=TagResource.encounter,
            organization=self.organization,
        )
        response = self.client.post(
            self.base_url,
            self.generate_tag_config_data(
                resource=TagResource.encounter,
                parent=parent_tag.external_id,
                organization=self.organization.external_id,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_detail_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(response.data["id"], get_response.data["id"])

    def test_create_tag_config_with_parent_with_different_resource_in_organization(
        self,
    ):
        """Test creating a tag config with parent with different resource in organization"""
        self.client.force_authenticate(user=self.superuser)
        parent_tag = self.create_tag_config(
            resource=TagResource.encounter,
            organization=self.organization,
        )
        response = self.client.post(
            self.base_url,
            self.generate_tag_config_data(
                resource=TagResource.patient.value,
                parent=parent_tag.external_id,
                organization=self.organization.external_id,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Parent tag config not found", status_code=400)

    # Test cases for update tagconfig

    def test_update_tag_config_as_superuser(self):
        """Test updating a tag config as superuser"""
        self.client.force_authenticate(user=self.superuser)
        tag_config = self.create_tag_config(
            resource=TagResource.encounter,
            priority=1,
            category=TagCategoryChoices.clinical.value,
        )
        response = self.client.put(
            self.get_detail_url(tag_config.external_id),
            self.generate_tag_config_data(
                resource=TagResource.encounter.value,
                category=TagCategoryChoices.lab.value,
                status=TagStatus.archived.value,
                priority=5,
                description="",
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_detail_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(response.data["id"], get_response.data["id"])
        self.assertEqual(get_response.data["priority"], 5)
        self.assertEqual(get_response.data["status"], TagStatus.archived.value)
        self.assertEqual(get_response.data["description"], "")

    def test_update_tag_config_as_with_facility_as_superuser(self):
        """Test updating a tag config with facility as superuser"""
        self.client.force_authenticate(user=self.superuser)
        tag_config = self.create_tag_config(
            resource=TagResource.encounter,
            facility=self.facility,
        )
        response = self.client.put(
            self.get_detail_url(tag_config.external_id),
            self.generate_tag_config_data(
                resource=TagResource.encounter.value,
                facility=self.facility.external_id,
                status=TagStatus.archived.value,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_detail_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(response.data["id"], get_response.data["id"])
        self.assertEqual(get_response.data["status"], TagStatus.archived.value)

    def test_update_tag_config_as_with_organization_as_superuser(self):
        """Test updating a tag config with organization as superuser"""
        self.client.force_authenticate(user=self.superuser)
        tag_config = self.create_tag_config(
            resource=TagResource.encounter,
            organization=self.organization,
        )
        response = self.client.put(
            self.get_detail_url(tag_config.external_id),
            self.generate_tag_config_data(
                resource=TagResource.encounter.value,
                organization=self.organization.external_id,
                status=TagStatus.archived.value,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_detail_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(response.data["id"], get_response.data["id"])
        self.assertEqual(get_response.data["status"], TagStatus.archived.value)

    def test_update_tag_config_as_with_global_as_superuser(self):
        """Test updating a global tag config as superuser"""
        self.client.force_authenticate(user=self.superuser)
        tag_config = self.create_tag_config(
            resource=TagResource.encounter,
        )
        response = self.client.put(
            self.get_detail_url(tag_config.external_id),
            self.generate_tag_config_data(
                resource=TagResource.encounter.value,
                status=TagStatus.archived.value,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_detail_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(response.data["id"], get_response.data["id"])
        self.assertEqual(get_response.data["status"], TagStatus.archived.value)

    def test_update_tag_config_with_facility_as_user_with_permission(self):
        """Test updating a tag config with facility as user with permission"""
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(self.user)
        tag_config = self.create_tag_config(
            resource=TagResource.encounter,
            facility=self.facility,
        )
        response = self.client.put(
            self.get_detail_url(tag_config.external_id),
            self.generate_tag_config_data(
                resource=TagResource.encounter.value,
                facility=self.facility.external_id,
                status=TagStatus.archived.value,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_detail_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(response.data["id"], get_response.data["id"])
        self.assertEqual(get_response.data["status"], TagStatus.archived.value)

    def test_update_tag_config_with_organization_as_user_without_permission(self):
        """Test updating a tag config with organization as user without permission"""
        self.client.force_authenticate(self.user)
        tag_config = self.create_tag_config(
            resource=TagResource.encounter,
            organization=self.organization,
        )
        response = self.client.put(
            self.get_detail_url(tag_config.external_id),
            self.generate_tag_config_data(
                resource=TagResource.encounter.value,
                organization=self.organization.external_id,
                status=TagStatus.archived.value,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "You do not have permission to write tag configs", status_code=403
        )

    def test_update_tag_config_with_organization_as_user_with_permission(self):
        """Test updating a tag config with organization as user with permission"""
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(self.user)
        tag_config = self.create_tag_config(
            resource=TagResource.encounter,
            organization=self.organization,
        )
        response = self.client.put(
            self.get_detail_url(tag_config.external_id),
            self.generate_tag_config_data(
                resource=TagResource.encounter.value,
                status=TagStatus.archived.value,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "You do not have permission to write tag configs", status_code=403
        )

    def test_update_tag_config_with_facility_organization_as_user_with_permission(self):
        """Test updating a tag config with facility organization as user with permission"""
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(self.user)
        tag_config = self.create_tag_config(
            resource=TagResource.encounter,
            facility=self.facility,
            organization=self.organization,
        )
        response = self.client.put(
            self.get_detail_url(tag_config.external_id),
            self.generate_tag_config_data(
                resource=TagResource.encounter.value,
                status=TagStatus.archived.value,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_detail_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(response.data["id"], get_response.data["id"])
        self.assertEqual(get_response.data["status"], TagStatus.archived.value)

    def test_update_tag_config_with_facility_user_without_permission(self):
        """Test updating a tag config with facility as user without permission"""
        self.client.force_authenticate(self.user)
        tag_config = self.create_tag_config(
            resource=TagResource.encounter,
            facility=self.facility,
        )
        response = self.client.put(
            self.get_detail_url(tag_config.external_id),
            self.generate_tag_config_data(
                resource=TagResource.encounter.value,
                status=TagStatus.archived.value,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "You do not have permission to write tag configs", status_code=403
        )

    # Test cases for retrieve tagconfig

    def test_retrieve_tag_config_as_superuser(self):
        """Test retrieving a tag config as superuser"""
        self.client.force_authenticate(user=self.superuser)
        tag_config = self.create_tag_config(
            resource=TagResource.encounter,
            priority=1,
            category=TagCategoryChoices.clinical.value,
        )
        response = self.client.get(self.get_detail_url(tag_config.external_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["priority"], 1)
        self.assertEqual(response.data["category"], TagCategoryChoices.clinical.value)

    def test_retrieve_tag_config_with_facility_as_superuser(self):
        """Test retrieving a tag config with facility as superuser"""
        self.client.force_authenticate(user=self.superuser)
        tag_config = self.create_tag_config(
            resource=TagResource.encounter,
            facility=self.facility,
        )
        response = self.client.get(self.get_detail_url(tag_config.external_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(tag_config.external_id))

    def test_retrieve_tag_config_with_organization_as_superuser(self):
        """Test retrieving a tag config with organization as superuser"""
        self.client.force_authenticate(user=self.superuser)
        tag_config = self.create_tag_config(
            resource=TagResource.encounter,
            organization=self.organization,
        )
        response = self.client.get(self.get_detail_url(tag_config.external_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(tag_config.external_id))

    def test_retrieve_tag_config_with_global_as_superuser(self):
        """Test retrieving a global tag config as superuser"""
        self.client.force_authenticate(user=self.superuser)
        tag_config = self.create_tag_config(
            resource=TagResource.encounter,
        )
        response = self.client.get(self.get_detail_url(tag_config.external_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(tag_config.external_id))
        self.assertIsNone(response.data.get("facility"))
        self.assertIsNone(response.data.get("organization"))

    def test_retrieve_tag_config_with_facility_as_user_with_permission(self):
        """Test retrieving a tag config with facility as user with permission"""
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(self.user)
        tag_config = self.create_tag_config(
            resource=TagResource.encounter,
            facility=self.facility,
        )
        response = self.client.get(self.get_detail_url(tag_config.external_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(tag_config.external_id))

    def test_retrieve_tag_config_with_facility_as_user_without_permission(self):
        """Test retrieving a tag config with facility as user without permission"""
        self.client.force_authenticate(self.user)
        tag_config = self.create_tag_config(
            resource=TagResource.encounter,
            facility=self.facility,
        )
        response = self.client.get(self.get_detail_url(tag_config.external_id))
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "You do not have permission to read tag configs", status_code=403
        )

    def test_retrieve_tag_config_with_organization_as_user_without_permission(self):
        """Test retrieving a tag config with organization as user without permission"""
        self.client.force_authenticate(self.user)
        tag_config = self.create_tag_config(
            resource=TagResource.encounter,
            organization=self.organization,
        )
        response = self.client.get(self.get_detail_url(tag_config.external_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(tag_config.external_id))

    def test_retrieve_tag_config_global_as_user_with_permission(self):
        """Test retrieving a global tag config as user with permission"""
        self.client.force_authenticate(self.user)
        tag_config = self.create_tag_config(
            resource=TagResource.encounter,
        )
        response = self.client.get(self.get_detail_url(tag_config.external_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(tag_config.external_id))

    # Testcases for listing & filtering tag configs

    def test_list_tag_configs_global_as_superuser(self):
        """Test listing global tag configs as superuser"""
        self.client.force_authenticate(user=self.superuser)
        tag_config1 = self.create_tag_config(resource=TagResource.encounter, priority=1)
        self.create_tag_config(
            resource=TagResource.encounter,
            priority=2,
            facility=self.facility,
        )

        response = self.client.get(self.base_url, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(tag_config1.external_id)
        )

    def test_list_tag_configs_with_facility_as_superuser(self):
        """Test listing tag configs with facility as superuser"""
        self.client.force_authenticate(user=self.superuser)
        tag_config1 = self.create_tag_config(
            resource=TagResource.encounter,
            priority=1,
            facility=self.facility,
        )
        self.create_tag_config(resource=TagResource.encounter, priority=2)

        response = self.client.get(
            self.base_url,
            {"facility": self.facility.external_id, "facility_only": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(tag_config1.external_id)
        )

    def test_list_tag_configs_global_as_user(self):
        """Test listing global tag configs as user"""
        self.client.force_authenticate(user=self.user)
        tag_config1 = self.create_tag_config(resource=TagResource.encounter, priority=1)
        self.create_tag_config(
            resource=TagResource.encounter,
            priority=2,
            facility=self.facility,
        )

        response = self.client.get(self.base_url, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(tag_config1.external_id)
        )

    def test_list_tag_configs_with_facility_as_user_with_permission(self):
        """Test listing tag configs with facility as user with permission"""
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(self.user)
        tag_config1 = self.create_tag_config(
            resource=TagResource.encounter,
            priority=1,
            facility=self.facility,
        )
        self.create_tag_config(resource=TagResource.encounter, priority=2)

        response = self.client.get(
            self.base_url,
            {"facility": self.facility.external_id, "facility_only": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(tag_config1.external_id)
        )

    def test_list_tag_configs_with_facility_as_user_without_permission(self):
        """Test listing tag configs with facility as user without permission"""
        self.client.force_authenticate(self.user)
        self.create_tag_config(
            resource=TagResource.encounter,
            priority=1,
            facility=self.facility,
        )
        self.create_tag_config(resource=TagResource.encounter, priority=2)

        response = self.client.get(
            self.base_url, {"facility": self.facility.external_id}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "You do not have permission to read tag configs", status_code=403
        )

    def test_list_tag_configs_with_organization_as_superuser(self):
        """Test listing tag configs with organization as superuser"""
        self.client.force_authenticate(user=self.superuser)
        tag_config1 = self.create_tag_config(
            resource=TagResource.encounter,
            priority=1,
            organization=self.organization,
        )
        self.create_tag_config(resource=TagResource.encounter, priority=2)
        response = self.client.get(
            self.base_url,
            {"organization": self.organization.external_id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(tag_config1.external_id)
        )

    def test_list_tag_configs_with_organization_as_user_with_permission(self):
        """Test listing tag configs with organization as user with permission"""
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(self.user)
        tag_config1 = self.create_tag_config(
            resource=TagResource.encounter,
            priority=1,
            organization=self.organization,
        )
        tag_config2 = self.create_tag_config(
            resource=TagResource.encounter,
            priority=2,
            organization=self.organization,
        )
        response = self.client.get(
            self.base_url,
            {"organization": self.organization.external_id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(
            response.data["results"][0]["id"], str(tag_config2.external_id)
        )
        self.assertEqual(
            response.data["results"][1]["id"], str(tag_config1.external_id)
        )

    def test_list_tag_configs_with_organization_as_user_without_permission(self):
        """Test listing tag configs with organization as user without permission"""
        self.client.force_authenticate(self.user)
        tag_config1 = self.create_tag_config(
            resource=TagResource.encounter,
            priority=1,
            organization=self.organization,
        )
        self.create_tag_config(slug="tag2", resource=TagResource.encounter, priority=2)
        response = self.client.get(
            self.base_url,
            {"organization": self.organization.external_id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(tag_config1.external_id)
        )

    def test_list_global_tag_configs_with_resource_as_user(self):
        """Test listing global tag configs with resource as user"""
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(self.user)
        self.create_tag_config(
            resource=TagResource.encounter,
            priority=1,
            organization=self.organization,
        )
        self.create_tag_config(
            resource=TagResource.encounter,
            priority=2,
            organization=self.organization,
        )
        self.create_tag_config(
            resource=TagResource.patient,
            priority=3,
            organization=self.organization,
        )
        response = self.client.get(
            self.base_url, {"resource": TagResource.encounter}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        for tag in response.data["results"]:
            self.assertEqual(tag["resource"], TagResource.encounter.value)

    def test_list_tag_configs_with_resource_in_a_facility_as_user_with_permission(self):
        """Test listing tag configs with resource in a facility as user with permission"""
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(self.user)
        self.create_tag_config(
            resource=TagResource.encounter,
            priority=1,
            facility=self.facility,
        )
        self.create_tag_config(
            resource=TagResource.encounter,
            priority=2,
            facility=self.facility,
        )
        self.create_tag_config(
            resource=TagResource.patient,
            priority=3,
            facility=self.facility,
        )
        response = self.client.get(
            self.base_url,
            {"resource": TagResource.encounter, "facility": self.facility.external_id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        for tag in response.data["results"]:
            self.assertEqual(tag["resource"], TagResource.encounter.value)

    def test_list_tag_configs_with_resource_in_a_facility_as_user_without_permission(
        self,
    ):
        """Test listing tag configs with resource in a facility as user without permission"""
        self.client.force_authenticate(self.user)
        self.create_tag_config(
            resource=TagResource.encounter,
            priority=1,
            facility=self.facility,
        )
        self.create_tag_config(
            resource=TagResource.encounter,
            priority=2,
            facility=self.facility,
        )
        response = self.client.get(
            self.base_url,
            {"resource": TagResource.encounter, "facility": self.facility.external_id},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "You do not have permission to read tag configs", status_code=403
        )

    def test_list_tag_configs_with_status_global(self):
        """Test listing tag configs with status global"""
        self.client.force_authenticate(self.user)
        tag_config1 = self.create_tag_config(
            resource=TagResource.encounter,
            priority=1,
            status=TagStatus.active,
        )
        self.create_tag_config(
            resource=TagResource.encounter,
            priority=2,
            status=TagStatus.archived,
        )
        response = self.client.get(
            self.base_url, {"status": TagStatus.active}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(tag_config1.external_id)
        )

    def test_list_tag_configs_with_status_in_a_facility_as_user_with_permission(self):
        """Test listing tag configs with status in a facility as user with permission"""
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(self.user)
        tag_config1 = self.create_tag_config(
            resource=TagResource.encounter,
            priority=1,
            status=TagStatus.active,
            facility=self.facility,
        )
        self.create_tag_config(
            resource=TagResource.encounter,
            priority=2,
            status=TagStatus.archived,
            facility=self.facility,
        )
        response = self.client.get(
            self.base_url,
            {"status": TagStatus.active, "facility": self.facility.external_id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(tag_config1.external_id)
        )

    def test_list_tag_configs_with_facility_organization_as_user_with_permission(self):
        """Test listing tag configs with facility organization as user with permission"""
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(self.user)
        tag_config1 = self.create_tag_config(
            resource=TagResource.encounter,
            priority=1,
            status=TagStatus.active,
            facility=self.facility,
            facility_organization=self.facility_organization,
        )
        tag_config2 = self.create_tag_config(
            resource=TagResource.encounter,
            priority=2,
            status=TagStatus.archived,
            facility=self.facility,
            facility_organization=self.facility_organization,
        )
        self.create_tag_config(
            resource=TagResource.encounter,
            priority=3,
            status=TagStatus.archived,
            facility=self.facility,
        )
        response = self.client.get(
            self.base_url,
            {
                "facility_organization": self.facility_organization.external_id,
                "facility": self.facility.external_id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(
            response.data["results"][0]["id"], str(tag_config2.external_id)
        )
        self.assertEqual(
            response.data["results"][1]["id"], str(tag_config1.external_id)
        )

    def test_list_tag_configs_with_facility_organization_as_user_without_permission(
        self,
    ):
        """Test listing tag configs with facility organization as user without permission"""
        self.client.force_authenticate(self.user)
        self.create_tag_config(
            resource=TagResource.encounter,
            priority=1,
            status=TagStatus.active,
            facility=self.facility,
            facility_organization=self.facility_organization,
        )
        self.create_tag_config(
            resource=TagResource.encounter,
            priority=2,
            status=TagStatus.archived,
            facility=self.facility,
            facility_organization=self.facility_organization,
        )
        response = self.client.get(
            self.base_url,
            {
                "facility_organization": self.facility_organization.external_id,
                "facility": self.facility.external_id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "You do not have permission to read tag configs", status_code=403
        )

    def test_list_tag_configs_with_facility_organization_as_superuser(self):
        """Test listing tag configs with facility organization as superuser"""
        self.client.force_authenticate(self.superuser)
        tag_config1 = self.create_tag_config(
            resource=TagResource.encounter,
            priority=1,
            status=TagStatus.active,
            facility=self.facility,
            facility_organization=self.facility_organization,
        )
        tag_config2 = self.create_tag_config(
            resource=TagResource.encounter,
            priority=2,
            status=TagStatus.archived,
            facility=self.facility,
            facility_organization=self.facility_organization,
        )
        response = self.client.get(
            self.base_url,
            {
                "facility_organization": self.facility_organization.external_id,
                "facility": self.facility.external_id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(
            response.data["results"][0]["id"], str(tag_config2.external_id)
        )
        self.assertEqual(
            response.data["results"][1]["id"], str(tag_config1.external_id)
        )

    def test_list_tag_configs_with_category_as_superuser(self):
        """Test listing tag configs with category as superuser"""
        self.client.force_authenticate(user=self.superuser)
        tag_config1 = self.create_tag_config(
            resource=TagResource.encounter,
            priority=1,
            category=TagCategoryChoices.clinical.value,
        )
        self.create_tag_config(
            resource=TagResource.encounter,
            priority=2,
            category=TagCategoryChoices.lab.value,
        )
        response = self.client.get(
            self.base_url,
            {"category": TagCategoryChoices.clinical.value},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(tag_config1.external_id)
        )

    def test_list_tag_configs_with_category_in_a_facility_as_user_with_permission(self):
        """Test listing tag configs with category in a facility as user with permission"""
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(self.user)
        tag_config1 = self.create_tag_config(
            resource=TagResource.encounter,
            priority=1,
            category=TagCategoryChoices.clinical.value,
            facility=self.facility,
        )
        self.create_tag_config(
            resource=TagResource.encounter,
            priority=2,
            category=TagCategoryChoices.lab.value,
            facility=self.facility,
        )
        response = self.client.get(
            self.base_url,
            {
                "category": TagCategoryChoices.clinical.value,
                "facility": self.facility.external_id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(tag_config1.external_id)
        )

    def test_list_tag_configs_with_category_in_a_facility_as_user_without_permission(
        self,
    ):
        """Test listing tag configs with category in a facility as user without permission"""
        self.client.force_authenticate(self.user)
        self.create_tag_config(
            resource=TagResource.encounter,
            priority=1,
            category=TagCategoryChoices.clinical.value,
            facility=self.facility,
        )
        self.create_tag_config(
            resource=TagResource.encounter,
            priority=2,
            category=TagCategoryChoices.lab.value,
            facility=self.facility,
        )
        response = self.client.get(
            self.base_url,
            {
                "category": TagCategoryChoices.clinical.value,
                "facility": self.facility.external_id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "You do not have permission to read tag configs", status_code=403
        )

    def test_list_tag_configs_with_category_in_a_facility_as_superuser(self):
        """Test listing tag configs with category in a facility as superuser"""
        self.client.force_authenticate(self.superuser)
        tag_config1 = self.create_tag_config(
            resource=TagResource.encounter,
            priority=1,
            category=TagCategoryChoices.clinical.value,
            facility=self.facility,
        )
        self.create_tag_config(
            resource=TagResource.encounter,
            priority=2,
            category=TagCategoryChoices.lab.value,
            facility=self.facility,
        )
        response = self.client.get(
            self.base_url,
            {
                "category": TagCategoryChoices.clinical.value,
                "facility": self.facility.external_id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(tag_config1.external_id)
        )

    def test_list_tag_configs_with_parent_as_superuser(self):
        """Test listing tag configs with parent as superuser"""
        self.client.force_authenticate(user=self.superuser)
        parent_tag = self.create_tag_config(
            resource=TagResource.encounter,
            priority=1,
            category=TagCategoryChoices.clinical.value,
        )
        self.create_tag_config(
            resource=TagResource.encounter,
            parent=parent_tag,
        )
        self.create_tag_config(
            resource=TagResource.encounter,
            parent=parent_tag,
        )
        response = self.client.get(
            self.base_url, {"parent": parent_tag.external_id}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        for tag in response.data["results"]:
            self.assertEqual(tag["parent"]["id"], str(parent_tag.external_id))

    def test_list_tag_configs_with_parent_in_a_facility_as_user_with_permission(self):
        """Test listing tag configs with parent in a facility as user with permission"""
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(self.user)
        parent_tag = self.create_tag_config(
            resource=TagResource.encounter,
            priority=1,
            category=TagCategoryChoices.clinical.value,
            facility=self.facility,
        )
        self.create_tag_config(
            resource=TagResource.encounter,
            parent=parent_tag,
            facility=self.facility,
        )
        self.create_tag_config(
            resource=TagResource.encounter,
            parent=parent_tag,
            facility=self.facility,
        )
        response = self.client.get(
            self.base_url,
            {"parent": parent_tag.external_id, "facility": self.facility.external_id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        for tag in response.data["results"]:
            self.assertEqual(tag["parent"]["id"], str(parent_tag.external_id))

    def test_list_tag_configs_with_parent_in_a_facility_as_user_without_permission(
        self,
    ):
        """Test listing tag configs with parent in a facility as user without permission"""
        self.client.force_authenticate(self.user)
        parent_tag = self.create_tag_config(
            resource=TagResource.encounter,
            priority=1,
            category=TagCategoryChoices.clinical.value,
            facility=self.facility,
        )
        self.create_tag_config(
            resource=TagResource.encounter,
            parent=parent_tag,
            facility=self.facility,
        )
        self.create_tag_config(
            resource=TagResource.encounter,
            parent=parent_tag,
            facility=self.facility,
        )
        response = self.client.get(
            self.base_url,
            {"parent": parent_tag.external_id, "facility": self.facility.external_id},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "You do not have permission to read tag configs", status_code=403
        )

    def test_list_tag_configs_with_parent_in_a_facility_as_superuser(self):
        """Test listing tag configs with parent in a facility as superuser"""
        self.client.force_authenticate(self.superuser)
        parent_tag = self.create_tag_config(
            resource=TagResource.encounter,
            priority=1,
            category=TagCategoryChoices.clinical.value,
            facility=self.facility,
        )
        self.create_tag_config(
            resource=TagResource.encounter,
            parent=parent_tag,
            facility=self.facility,
        )
        self.create_tag_config(
            resource=TagResource.encounter,
            parent=parent_tag,
            facility=self.facility,
        )
        response = self.client.get(
            self.base_url,
            {"parent": parent_tag.external_id, "facility": self.facility.external_id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        for tag in response.data["results"]:
            self.assertEqual(tag["parent"]["id"], str(parent_tag.external_id))

    def test_list_tag_configs_with_parent_null_as_superuser(self):
        """Test listing tag configs with parent null as superuser"""
        self.client.force_authenticate(user=self.superuser)
        tag_config1 = self.create_tag_config(resource=TagResource.encounter, priority=3)
        self.create_tag_config(
            resource=TagResource.encounter, priority=2, parent=tag_config1
        )
        tag_config3 = self.create_tag_config(resource=TagResource.encounter, priority=1)
        response = self.client.get(
            self.base_url, {"parent_is_null": True}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(
            response.data["results"][0]["id"], str(tag_config3.external_id)
        )
        self.assertEqual(
            response.data["results"][1]["id"], str(tag_config1.external_id)
        )

    def test_list_tag_configs_with_parent_null_as_true_in_a_facility_as_user_with_permission(
        self,
    ):
        """Test listing tag configs with parent null as true in a facility as user with permission to fetch only parent tags"""
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(self.user)
        tag_config1 = self.create_tag_config(
            resource=TagResource.encounter,
            priority=3,
            facility=self.facility,
        )
        self.create_tag_config(
            resource=TagResource.encounter,
            priority=2,
            parent=tag_config1,
            facility=self.facility,
        )
        tag_config3 = self.create_tag_config(
            resource=TagResource.encounter,
            priority=1,
            facility=self.facility,
        )
        response = self.client.get(
            self.base_url,
            {"parent_is_null": True, "facility": self.facility.external_id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(
            response.data["results"][0]["id"], str(tag_config3.external_id)
        )
        self.assertEqual(
            response.data["results"][1]["id"], str(tag_config1.external_id)
        )

    def test_list_tag_configs_with_parent_null_in_a_facility_as_user_without_permission(
        self,
    ):
        """Test listing tag configs with parent null in a facility as user without permission"""
        self.client.force_authenticate(self.user)
        tag_config1 = self.create_tag_config(
            resource=TagResource.encounter,
            priority=3,
            facility=self.facility,
        )
        self.create_tag_config(
            resource=TagResource.encounter,
            priority=2,
            parent=tag_config1,
            facility=self.facility,
        )
        self.create_tag_config(
            resource=TagResource.encounter,
            priority=1,
            facility=self.facility,
        )
        response = self.client.get(
            self.base_url,
            {"parent_is_null": True, "facility": self.facility.external_id},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "You do not have permission to read tag configs", status_code=403
        )

    def test_list_tag_configs_with_parent_null_as_true_in_a_facility_as_superuser(self):
        """Test listing tag configs with parent null as true in a facility as superuser to fetch only parent tags"""
        self.client.force_authenticate(self.superuser)
        tag_config1 = self.create_tag_config(
            resource=TagResource.encounter,
            priority=3,
            facility=self.facility,
        )
        self.create_tag_config(
            resource=TagResource.encounter,
            priority=2,
            parent=tag_config1,
            facility=self.facility,
        )
        tag_config3 = self.create_tag_config(
            resource=TagResource.encounter,
            priority=1,
            facility=self.facility,
        )
        response = self.client.get(
            self.base_url,
            {"parent_is_null": True, "facility": self.facility.external_id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(
            response.data["results"][0]["id"], str(tag_config3.external_id)
        )
        self.assertEqual(
            response.data["results"][1]["id"], str(tag_config1.external_id)
        )

    def test_list_tag_configs_with_parent_null_as_false_in_a_facility_as_superuser(
        self,
    ):
        """Test listing tag configs with parent null as false in a facility as superuser to fetch only child tags"""
        self.client.force_authenticate(self.superuser)
        tag_config1 = self.create_tag_config(
            resource=TagResource.encounter,
            priority=3,
            facility=self.facility,
        )
        tag_config2 = self.create_tag_config(
            resource=TagResource.encounter,
            priority=2,
            parent=tag_config1,
            facility=self.facility,
        )
        self.create_tag_config(
            resource=TagResource.encounter,
            priority=1,
            facility=self.facility,
        )
        response = self.client.get(
            self.base_url,
            {"parent_is_null": False, "facility": self.facility.external_id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(tag_config2.external_id)
        )

    def test_list_tag_configs_with_display_as_user(self):
        """Test listing tag configs with display in a facility as user"""
        self.client.force_authenticate(user=self.user)
        self.create_tag_config(
            resource=TagResource.encounter,
            priority=1,
            display="Test Tag 1",
        )
        self.create_tag_config(
            resource=TagResource.encounter,
            priority=2,
            display="Test Tag 2",
        )
        response = self.client.get(
            self.base_url, {"display": "Test Tag"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        for tag in response.data["results"]:
            self.assertIn("Test Tag", tag["display"])

    def test_list_tag_configs_with_display_in_a_facility_as_user_with_permission(self):
        """Test listing tag configs with display in a facility as user with permission"""
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(self.user)
        self.create_tag_config(
            resource=TagResource.encounter,
            priority=1,
            display="Test Tag 1",
            facility=self.facility,
        )
        self.create_tag_config(
            resource=TagResource.encounter,
            priority=2,
            display="Test Tag 2",
            facility=self.facility,
        )
        response = self.client.get(
            self.base_url,
            {"display": "Test Tag", "facility": self.facility.external_id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        for tag in response.data["results"]:
            self.assertIn("Test Tag", tag["display"])

    def test_list_tag_configs_with_display_in_a_facility_as_user_without_permission(
        self,
    ):
        """Test listing tag configs with display in a facility as user without permission"""
        self.client.force_authenticate(self.user)
        self.create_tag_config(
            resource=TagResource.encounter,
            priority=1,
            display="Test Tag 1",
            facility=self.facility,
        )
        self.create_tag_config(
            resource=TagResource.encounter,
            priority=2,
            display="Test Tag 2",
            facility=self.facility,
        )
        response = self.client.get(
            self.base_url,
            {"display": "Test Tag", "facility": self.facility.external_id},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "You do not have permission to read tag configs", status_code=403
        )

    def test_list_tag_configs_with_display_in_a_facility_as_superuser(self):
        """Test listing tag configs with display in a facility as superuser"""
        self.client.force_authenticate(self.superuser)
        self.create_tag_config(
            resource=TagResource.encounter,
            priority=1,
            display="Test Tag 1",
            facility=self.facility,
        )
        self.create_tag_config(
            resource=TagResource.encounter,
            priority=2,
            display="Test Tag 2",
            facility=self.facility,
        )
        response = self.client.get(
            self.base_url,
            {"display": "Test Tag", "facility": self.facility.external_id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        for tag in response.data["results"]:
            self.assertIn("Test Tag", tag["display"])

    def test_list_tag_configs_with_ids_as_user(self):
        """Test listing tag configs with ids in a facility as user"""
        self.client.force_authenticate(user=self.user)
        tag_config1 = self.create_tag_config(resource=TagResource.encounter)
        tag_config2 = self.create_tag_config(resource=TagResource.encounter)
        self.create_tag_config(slug="tag3", resource=TagResource.encounter)
        response = self.client.get(
            self.base_url,
            {"ids": f"{tag_config1.external_id},{tag_config2.external_id}"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(
            response.data["results"][0]["id"], str(tag_config2.external_id)
        )
        self.assertEqual(
            response.data["results"][1]["id"], str(tag_config1.external_id)
        )

    def test_list_tag_configs_with_ids_in_a_facility_as_user_with_permission(self):
        """Test listing tag configs with ids in a facility as user with permission"""
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(self.user)
        tag_config1 = self.create_tag_config(
            resource=TagResource.encounter, facility=self.facility
        )
        tag_config2 = self.create_tag_config(
            resource=TagResource.encounter, facility=self.facility
        )
        self.create_tag_config(resource=TagResource.encounter, facility=self.facility)
        response = self.client.get(
            self.base_url,
            {
                "ids": f"{tag_config1.external_id},{tag_config2.external_id}",
                "facility": self.facility.external_id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(
            response.data["results"][0]["id"], str(tag_config2.external_id)
        )
        self.assertEqual(
            response.data["results"][1]["id"], str(tag_config1.external_id)
        )

    def test_list_tag_configs_with_ids_in_a_facility_as_user_without_permission(self):
        """Test listing tag configs with ids in a facility as user without permission"""
        self.client.force_authenticate(self.user)
        tag_config1 = self.create_tag_config(
            resource=TagResource.encounter, facility=self.facility
        )
        tag_config2 = self.create_tag_config(
            resource=TagResource.encounter, facility=self.facility
        )
        self.create_tag_config(resource=TagResource.encounter, facility=self.facility)
        response = self.client.get(
            self.base_url,
            {
                "ids": f"{tag_config1.external_id},{tag_config2.external_id}",
                "facility": self.facility.external_id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "You do not have permission to read tag configs", status_code=403
        )

    def test_list_tag_configs_with_ids_in_a_facility_as_superuser(self):
        """Test listing tag configs with ids in a facility as superuser"""
        self.client.force_authenticate(self.superuser)
        tag_config1 = self.create_tag_config(
            resource=TagResource.encounter, facility=self.facility
        )
        tag_config2 = self.create_tag_config(
            resource=TagResource.encounter, facility=self.facility
        )
        self.create_tag_config(resource=TagResource.encounter, facility=self.facility)
        response = self.client.get(
            self.base_url,
            {
                "ids": f"{tag_config1.external_id},{tag_config2.external_id}",
                "facility": self.facility.external_id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(
            response.data["results"][0]["id"], str(tag_config2.external_id)
        )
        self.assertEqual(
            response.data["results"][1]["id"], str(tag_config1.external_id)
        )
