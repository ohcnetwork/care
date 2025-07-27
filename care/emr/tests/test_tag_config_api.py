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
            "slug": slug or "test-tag",
            "display": "Test Tag",
            "description": "This is a test tag config",
            "category": category or TagCategoryChoices.clinical.value,
            "priority": 1,
            "resource": resource or TagResource.encounter.value,
            **kwargs,
        }

    def get_detail_url(self, external_id):
        return reverse("tag_config-detail", kwargs={"external_id": external_id})

    def create_tag_config(
        self, status=None, category=None, resource=None, slug=None, **kwargs
    ):
        tag_config_data = self.generate_tag_config_data(
            **kwargs,
            status=status,
            category=category,
            resource=resource,
            slug=slug,
        )
        return baker.make("emr.TagConfig", **tag_config_data)

    # Test cases for create tagconfig

    def test_create_tag_config_with_organization_as_superuser(self):
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
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.base_url, self.generate_tag_config_data(), format="json"
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_detail_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(response.data["id"], get_response.data["id"])

    def test_create_tag_config_with_only_facility_organization_as_superuser(self):
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
        self.client.force_authenticate(self.user)
        invalid_facility = str(uuid.uuid4())
        response = self.client.post(
            self.base_url,
            self.generate_tag_config_data(facility=invalid_facility),
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Object not found", status_code=404)

    def test_create_tag_config_as_user_with_invalid_facility_organization(self):
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
        self.client.force_authenticate(self.user)
        response = self.client.post(
            self.base_url,
            self.generate_tag_config_data(organization=str(uuid.uuid4())),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Organization not found", status_code=400)

    def test_create_tag_config_with_duplicate_slug_in_same_facility(self):
        self.client.force_authenticate(user=self.superuser)
        self.create_tag_config(facility=self.facility, slug="duplicate-slug")
        response = self.client.post(
            self.base_url,
            self.generate_tag_config_data(
                facility=self.facility.external_id, slug="duplicate-slug"
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Slug must be unique", status_code=400)

    def test_create_tag_config_with_duplicate_slug_in_different_facility(self):
        self.client.force_authenticate(user=self.superuser)
        tag = self.create_tag_config(facility=self.facility, slug="duplicate-slug")
        another_facility = self.create_facility(user=self.superuser)
        response = self.client.post(
            self.base_url,
            self.generate_tag_config_data(
                facility=another_facility.external_id, slug="duplicate-slug"
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["slug"], tag.slug)

    def test_create_tag_config_with_duplicate_slug_in_same_organization(self):
        self.client.force_authenticate(user=self.superuser)
        self.create_tag_config(organization=self.organization, slug="duplicate-slug")
        another_organization = self.create_organization(user=self.superuser)
        response = self.client.post(
            self.base_url,
            self.generate_tag_config_data(
                organization=another_organization.external_id, slug="duplicate-slug"
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Slug must be unique", status_code=400)

    def test_create_tag_config_with_duplicate_slug_in_global(self):
        self.client.force_authenticate(user=self.superuser)
        self.create_tag_config(slug="duplicate-slug")
        response = self.client.post(
            self.base_url,
            self.generate_tag_config_data(slug="duplicate-slug"),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Slug must be unique", status_code=400)

    def test_create_tag_config_with_parent_with_same_resource_globally(self):
        self.client.force_authenticate(user=self.superuser)
        parent_tag = self.create_tag_config(
            slug="parent-tag",
            resource=TagResource.encounter,
        )
        response = self.client.post(
            self.base_url,
            self.generate_tag_config_data(
                slug="child-tag",
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
        self.client.force_authenticate(user=self.superuser)
        parent_tag = self.create_tag_config(
            slug="parent-tag",
            resource=TagResource.encounter,
        )
        response = self.client.post(
            self.base_url,
            self.generate_tag_config_data(
                slug="child-tag",
                resource=TagResource.patient.value,
                parent=parent_tag.external_id,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Parent tag config not found", status_code=400)

    def test_create_tag_config_with_parent_with_same_resource_in_facility(self):
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        parent_tag = self.create_tag_config(
            slug="parent-tag",
            resource=TagResource.encounter,
            facility=self.facility,
        )
        response = self.client.post(
            self.base_url,
            self.generate_tag_config_data(
                slug="child-tag",
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

    def test_create_tag_config_with_parent_with_different_resource_in_facility(
        self,
    ):
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        parent_tag = self.create_tag_config(
            slug="parent-tag",
            resource=TagResource.encounter,
            facility=self.facility,
        )
        response = self.client.post(
            self.base_url,
            self.generate_tag_config_data(
                slug="child-tag",
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
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        parent_tag = self.create_tag_config(
            slug="parent-tag",
            resource=TagResource.encounter,
            facility=self.facility,
        )
        another_facility = self.create_facility(user=self.superuser)
        response = self.client.post(
            self.base_url,
            self.generate_tag_config_data(
                slug="child-tag",
                resource=TagResource.encounter,
                parent=parent_tag.external_id,
                facility=another_facility.external_id,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Parent tag config not found", status_code=400)

    def test_create_tag_config_with_parent_with_same_resource_in_organization(
        self,
    ):
        self.client.force_authenticate(user=self.superuser)
        parent_tag = self.create_tag_config(
            slug="parent-tag",
            resource=TagResource.encounter,
            organization=self.organization,
        )
        response = self.client.post(
            self.base_url,
            self.generate_tag_config_data(
                slug="child-tag",
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
        self.client.force_authenticate(user=self.superuser)
        parent_tag = self.create_tag_config(
            slug="parent-tag",
            resource=TagResource.encounter,
            organization=self.organization,
        )
        response = self.client.post(
            self.base_url,
            self.generate_tag_config_data(
                slug="child-tag",
                resource=TagResource.patient.value,
                parent=parent_tag.external_id,
                organization=self.organization.external_id,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Parent tag config not found", status_code=400)

    def test_create_tag_config_with_invalid_parent_slug_with_same_scope(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.base_url,
            self.generate_tag_config_data(
                slug="child-tag",
                resource=TagResource.encounter,
                parent=str(uuid.uuid4()),
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Parent tag config not found", status_code=400)

    # Test cases for update tagconfig

    def test_update_tag_config_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        tag_config = self.create_tag_config(
            slug="test-tag",
            resource=TagResource.encounter,
            priority=1,
            category=TagCategoryChoices.clinical.value,
        )
        response = self.client.put(
            self.get_detail_url(tag_config.external_id),
            self.generate_tag_config_data(
                slug="test-tag-updated",
                resource=TagResource.encounter.value,
                category=TagCategoryChoices.lab.value,
                status=TagStatus.archived.value,
                priority=5,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_detail_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(response.data["id"], get_response.data["id"])
        self.assertEqual(get_response.data["slug"], "test-tag-updated")
        self.assertEqual(get_response.data["priority"], 5)
        self.assertEqual(get_response.data["status"], TagStatus.archived.value)

    def test_update_tag_config_as_with_facility_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        tag_config = self.create_tag_config(
            slug="test-tag",
            resource=TagResource.encounter,
            facility=self.facility,
        )
        response = self.client.put(
            self.get_detail_url(tag_config.external_id),
            self.generate_tag_config_data(
                slug="test-tag-updated",
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
        self.assertEqual(get_response.data["slug"], "test-tag-updated")
        self.assertEqual(get_response.data["status"], TagStatus.archived.value)

    def test_update_tag_config_as_with_organization_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        tag_config = self.create_tag_config(
            slug="test-tag",
            resource=TagResource.encounter,
            organization=self.organization,
        )
        response = self.client.put(
            self.get_detail_url(tag_config.external_id),
            self.generate_tag_config_data(
                slug="test-tag-updated",
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
        self.assertEqual(get_response.data["slug"], "test-tag-updated")
        self.assertEqual(get_response.data["status"], TagStatus.archived.value)

    def test_update_tag_config_as_with_global_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        tag_config = self.create_tag_config(
            slug="test-tag",
            resource=TagResource.encounter,
        )
        response = self.client.put(
            self.get_detail_url(tag_config.external_id),
            self.generate_tag_config_data(
                slug="test-tag-updated",
                resource=TagResource.encounter.value,
                status=TagStatus.archived.value,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_detail_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(response.data["id"], get_response.data["id"])
        self.assertEqual(get_response.data["slug"], "test-tag-updated")
        self.assertEqual(get_response.data["status"], TagStatus.archived.value)

    def test_update_tag_config_with_facility_as_user_with_permission(self):
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(self.user)
        tag_config = self.create_tag_config(
            slug="test-tag",
            resource=TagResource.encounter,
            facility=self.facility,
        )
        response = self.client.put(
            self.get_detail_url(tag_config.external_id),
            self.generate_tag_config_data(
                slug="test-tag-updated",
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
        self.assertEqual(get_response.data["slug"], "test-tag-updated")
        self.assertEqual(get_response.data["status"], TagStatus.archived.value)

    def test_update_tag_config_with_organization_as_user_without_permission(self):
        self.client.force_authenticate(self.user)
        tag_config = self.create_tag_config(
            slug="test-tag",
            resource=TagResource.encounter,
            organization=self.organization,
        )
        response = self.client.put(
            self.get_detail_url(tag_config.external_id),
            self.generate_tag_config_data(
                slug="test-tag-updated",
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
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(self.user)
        tag_config = self.create_tag_config(
            slug="test-tag",
            resource=TagResource.encounter,
            organization=self.organization,
        )
        response = self.client.put(
            self.get_detail_url(tag_config.external_id),
            self.generate_tag_config_data(
                slug="test-tag-updated",
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
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(self.user)
        tag_config = self.create_tag_config(
            slug="test-tag",
            resource=TagResource.encounter,
            facility=self.facility,
            organization=self.organization,
        )
        response = self.client.put(
            self.get_detail_url(tag_config.external_id),
            self.generate_tag_config_data(
                slug="test-tag-updated",
                resource=TagResource.encounter.value,
                status=TagStatus.archived.value,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(self.get_detail_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(response.data["id"], get_response.data["id"])
        self.assertEqual(get_response.data["slug"], "test-tag-updated")
        self.assertEqual(get_response.data["status"], TagStatus.archived.value)

    # Test cases for retrieve tagconfig

    def test_retrieve_tag_config_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        tag_config = self.create_tag_config(
            slug="test-tag",
            resource=TagResource.encounter,
            priority=1,
            category=TagCategoryChoices.clinical.value,
        )
        response = self.client.get(self.get_detail_url(tag_config.external_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["slug"], "test-tag")
        self.assertEqual(response.data["priority"], 1)
        self.assertEqual(response.data["category"], TagCategoryChoices.clinical.value)

    def test_retrieve_tag_config_with_facility_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        tag_config = self.create_tag_config(
            slug="test-tag",
            resource=TagResource.encounter,
            facility=self.facility,
        )
        response = self.client.get(self.get_detail_url(tag_config.external_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["slug"], "test-tag")
        self.assertEqual(response.data["id"], str(tag_config.external_id))

    def test_retrieve_tag_config_with_organization_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        tag_config = self.create_tag_config(
            slug="test-tag",
            resource=TagResource.encounter,
            organization=self.organization,
        )
        response = self.client.get(self.get_detail_url(tag_config.external_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["slug"], "test-tag")
        self.assertEqual(response.data["id"], str(tag_config.external_id))

    def test_retrieve_tag_config_with_global_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        tag_config = self.create_tag_config(
            slug="test-tag",
            resource=TagResource.encounter,
        )
        response = self.client.get(self.get_detail_url(tag_config.external_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(tag_config.external_id))
        self.assertEqual(response.data["slug"], "test-tag")
        self.assertIsNone(response.data.get("facility"))
        self.assertIsNone(response.data.get("organization"))

    def test_retrieve_tag_config_with_facility_as_user_with_permission(self):
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(self.user)
        tag_config = self.create_tag_config(
            slug="test-tag",
            resource=TagResource.encounter,
            facility=self.facility,
        )
        response = self.client.get(self.get_detail_url(tag_config.external_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(tag_config.external_id))

    def test_retrieve_tag_config_with_organization_as_user_without_permission(self):
        self.client.force_authenticate(self.user)
        tag_config = self.create_tag_config(
            slug="test-tag",
            resource=TagResource.encounter,
            organization=self.organization,
        )
        response = self.client.get(self.get_detail_url(tag_config.external_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(tag_config.external_id))

    def test_retrieve_tag_config_global_as_user_with_permission(self):
        self.client.force_authenticate(self.user)
        tag_config = self.create_tag_config(
            slug="test-tag",
            resource=TagResource.encounter,
        )
        response = self.client.get(self.get_detail_url(tag_config.external_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(tag_config.external_id))
