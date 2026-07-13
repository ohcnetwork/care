from django.urls import reverse
from model_bakery import baker

from care.emr.models.activity_definition import ActivityDefinition
from care.emr.models.charge_item_definition import ChargeItemDefinition
from care.emr.models.product_knowledge import ProductKnowledge
from care.emr.models.resource_category import ResourceCategory
from care.security.permissions.resource_category import ResourceCategoryPermissions
from care.utils.tests.base import CareAPITestBase


class ResourceCategoryAPITestCase(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.super_user = self.create_super_user()
        self.user = self.create_user()
        self.facility = self.create_facility(
            user=self.super_user,
        )
        self.facility_organization = self.create_facility_organization(
            facility=self.facility, org_type="root"
        )
        self.permissions = [
            ResourceCategoryPermissions.can_write_resource_category.name,
            ResourceCategoryPermissions.can_read_resource_category.name,
        ]
        self.role = self.create_role_with_permissions(
            permissions=self.permissions,
        )
        self.url = reverse(
            "resource_category-list",
            kwargs={"facility_external_id": self.facility.external_id},
        )

    def get_url(self, facility):
        return reverse(
            "resource_category-list",
            kwargs={"facility_external_id": facility.external_id},
        )

    def get_detail_url(self, facility, resource_category):
        return reverse(
            "resource_category-detail",
            kwargs={
                "facility_external_id": facility.external_id,
                "slug": resource_category.slug,
            },
        )

    def generate_resource_category_data(self, **kwargs):
        data = {
            "title": kwargs.get("title", "Test Resource Category"),
            "description": kwargs.get("description", "Test Description"),
            "slug_value": kwargs.get("slug_value", "test-resource-category"),
            "resource_type": kwargs.get("resource_type", "product_knowledge"),
            "resource_sub_type": kwargs.get("resource_sub_type", "other"),
            "facility": kwargs.get("facility", self.facility.external_id),
            **kwargs,
        }
        data.update(kwargs)
        return data

    def calculate_slug(self, slug_value, facility):
        return f"f-{facility.external_id}-{slug_value}"

    def create_resource_category(self, slug_value, facility, **kwargs):
        data = {
            "title": kwargs.get("title", "Test Resource Category"),
            "description": kwargs.get("description", "Test Description"),
            "resource_type": kwargs.get("resource_type", "product_knowledge"),
            "resource_sub_type": kwargs.get("resource_sub_type", "other"),
            "facility": kwargs.get("facility", self.facility),
            **kwargs,
        }
        slug = self.calculate_slug(slug_value, facility)
        return baker.make(ResourceCategory, slug=slug, **data)

    # Test cases for create resource category api

    def test_create_resource_category_as_super_user(self):
        self.client.force_authenticate(user=self.super_user)
        data = self.generate_resource_category_data()
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 200)

    def test_create_resource_category_as_regular_user(self):
        self.client.force_authenticate(user=self.user)
        data = self.generate_resource_category_data()
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Access denied to resource category")

    def test_create_resource_category_with_parent(self):
        self.client.force_authenticate(user=self.super_user)
        parent_category = self.create_resource_category(
            slug_value="parent-category",
            facility=self.facility,
            title="Parent Category",
        )
        data = self.generate_resource_category_data(
            title="Child Category",
            slug_value="child-category",
            parent=parent_category.slug,
        )
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["parent"]["id"], str(parent_category.external_id)
        )

    def test_create_resource_category_with_parent_as_regular_user(self):
        self.client.force_authenticate(user=self.user)
        parent_category = self.create_resource_category(
            slug_value="parent-category",
            facility=self.facility,
            title="Parent Category",
        )
        data = self.generate_resource_category_data(
            title="Child Category",
            slug_value="child-category",
            parent=parent_category.slug,
        )
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Access denied to resource category")

    def test_create_resource_category_with_parent_of_different_resource_type(self):
        self.client.force_authenticate(user=self.super_user)
        parent_category = self.create_resource_category(
            slug_value="parent-category",
            facility=self.facility,
            title="Parent Category",
            resource_type="activity_definition",
        )
        data = self.generate_resource_category_data(
            title="Child Category",
            slug_value="child-category",
            parent=parent_category.slug,
            resource_type="product_knowledge",
        )
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "Parent category does not belong to same resource type",
        )

    def test_create_resource_category_with_parent_as_child_category(self):
        self.client.force_authenticate(user=self.super_user)
        parent_category = self.create_resource_category(
            slug_value="parent-category",
            facility=self.facility,
            title="Parent Category",
            is_child=True,
        )
        data = self.generate_resource_category_data(
            title="Child Category",
            slug_value="child-category",
            parent=parent_category.slug,
        )
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "Parent category is a child",
        )

    # Test cases for update resource category api

    def test_update_resource_category_as_super_user(self):
        self.client.force_authenticate(user=self.super_user)
        resource_category = self.create_resource_category(
            slug_value="test-category", facility=self.facility
        )
        url = self.get_detail_url(self.facility, resource_category)
        data = self.generate_resource_category_data(title="Updated Title")
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "Updated Title")

    def test_update_resource_category_as_regular_user_without_permission(self):
        self.client.force_authenticate(user=self.user)
        resource_category = self.create_resource_category(
            slug_value="test-category", facility=self.facility
        )
        url = self.get_detail_url(self.facility, resource_category)
        data = self.generate_resource_category_data(title="Updated Title")
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Access denied to resource category")

    def test_update_resource_category_as_regular_user_with_permission(self):
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        resource_category = self.create_resource_category(
            slug_value="test-category", facility=self.facility
        )
        url = self.get_detail_url(self.facility, resource_category)
        data = self.generate_resource_category_data(title="Updated Title")
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "Updated Title")

    # Testcases for list resource categories

    def test_list_resource_categories_as_super_user(self):
        self.client.force_authenticate(user=self.super_user)
        resource_category = self.create_resource_category(
            slug_value="test-category", facility=self.facility
        )
        url = self.get_url(self.facility)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(resource_category.external_id)
        )

    def test_list_resource_categories_as_regular_user_without_permission(self):
        self.client.force_authenticate(user=self.user)
        self.create_resource_category(
            slug_value="test-category", facility=self.facility
        )
        url = self.get_url(self.facility)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Access denied to resource category")

    def test_list_resource_categories_as_regular_user_with_permission(self):
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        resource_category = self.create_resource_category(
            slug_value="test-category", facility=self.facility
        )
        url = self.get_url(self.facility)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(resource_category.external_id)
        )

    def test_list_resource_categories_with_parent_filter(self):
        self.client.force_authenticate(user=self.super_user)
        parent_category = self.create_resource_category(
            slug_value="parent-category",
            facility=self.facility,
            title="Parent Category",
        )
        child_category = self.create_resource_category(
            slug_value="child-category",
            facility=self.facility,
            title="Child Category",
            parent=parent_category,
        )
        parent_slug = self.calculate_slug("parent-category", self.facility)
        response = self.client.get(
            self.get_url(self.facility) + f"?parent={parent_slug}", format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(child_category.external_id)
        )
        self.assertEqual(response.data["results"][0]["title"], "Child Category")

    def test_list_resource_categories_with_parent_filter_no_results(self):
        self.client.force_authenticate(user=self.super_user)
        parent_category = self.create_resource_category(
            slug_value="parent-category",
            facility=self.facility,
            title="Parent Category",
        )
        self.create_resource_category(
            slug_value="child-category",
            facility=self.facility,
            title="Child Category",
            parent=parent_category,
        )
        response = self.client.get(
            self.get_url(self.facility) + "?parent=", format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(parent_category.external_id)
        )

    # Test cases for retrieve resource category api

    def test_retrieve_resource_category_as_super_user(self):
        self.client.force_authenticate(user=self.super_user)
        resource_category = self.create_resource_category(
            slug_value="test-category", facility=self.facility
        )
        url = self.get_detail_url(self.facility, resource_category)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(resource_category.external_id))

    def test_retrieve_resource_category_as_regular_user_without_permission(self):
        self.client.force_authenticate(user=self.user)
        resource_category = self.create_resource_category(
            slug_value="test-category", facility=self.facility
        )
        url = self.get_detail_url(self.facility, resource_category)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Access denied to resource category")

    def test_retrieve_resource_category_as_regular_user_with_permission(self):
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        resource_category = self.create_resource_category(
            slug_value="test-category", facility=self.facility
        )
        url = self.get_detail_url(self.facility, resource_category)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(resource_category.external_id))

    # Test cases for set_monetary_components action

    def get_set_monetary_components_url(self, facility, resource_category):
        return reverse(
            "resource_category-set-monetary-components",
            kwargs={
                "facility_external_id": facility.external_id,
                "slug": resource_category.slug,
            },
        )

    def test_set_monetary_components_as_super_user(self):
        self.client.force_authenticate(user=self.super_user)
        resource_category = self.create_resource_category(
            slug_value="charge-item",
            facility=self.facility,
            resource_type="charge_item_definition",
        )
        url = self.get_set_monetary_components_url(self.facility, resource_category)
        data = [
            {
                "monetary_component_type": "surcharge",
                "code": {"system": "http://example.com", "code": "surcharge-1"},
                "amount": "100.00",
            },
        ]
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        resource_category.refresh_from_db()
        self.assertEqual(len(resource_category.configured_monetary_components), 1)
        self.assertEqual(
            resource_category.configured_monetary_components[0][
                "monetary_component_type"
            ],
            "surcharge",
        )

    def test_set_monetary_components_as_regular_user_without_permission(self):
        self.client.force_authenticate(user=self.user)
        resource_category = self.create_resource_category(
            slug_value="charge-item",
            facility=self.facility,
            resource_type="charge_item_definition",
        )
        url = self.get_set_monetary_components_url(self.facility, resource_category)
        data = [
            {
                "monetary_component_type": "base",
                "code": {"system": "http://example.com", "code": "base-1"},
                "amount": "100.00",
            },
        ]
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Access denied to resource category")

    def test_set_monetary_components_as_regular_user_with_permission(self):
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        resource_category = self.create_resource_category(
            slug_value="charge-item",
            facility=self.facility,
            resource_type="charge_item_definition",
        )
        url = self.get_set_monetary_components_url(self.facility, resource_category)
        data = [
            {
                "monetary_component_type": "tax",
                "code": {"system": "http://example.com", "code": "tax-1"},
                "factor": "0.18",
            },
        ]
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        resource_category.refresh_from_db()
        self.assertEqual(len(resource_category.configured_monetary_components), 1)

    def test_set_monetary_components_on_non_charge_item_definition(self):
        self.client.force_authenticate(user=self.super_user)
        resource_category = self.create_resource_category(
            slug_value="product-category",
            facility=self.facility,
            resource_type="product_knowledge",
        )
        url = self.get_set_monetary_components_url(self.facility, resource_category)
        data = [
            {
                "monetary_component_type": "surcharge",
                "code": {"system": "http://example.com", "code": "surcharge-1"},
                "amount": "50.00",
            },
        ]
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "Resource category is not a charge item definition",
        )

    def test_set_monetary_components_with_base_component_rejected(self):
        self.client.force_authenticate(user=self.super_user)
        resource_category = self.create_resource_category(
            slug_value="charge-item",
            facility=self.facility,
            resource_type="charge_item_definition",
        )
        url = self.get_set_monetary_components_url(self.facility, resource_category)
        data = [
            {
                "monetary_component_type": "base",
                "amount": "500.00",
            },
        ]
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "Base component is not allowed in configured monetary components",
        )

    def test_set_monetary_components_with_empty_list(self):
        self.client.force_authenticate(user=self.super_user)
        resource_category = self.create_resource_category(
            slug_value="charge-item",
            facility=self.facility,
            resource_type="charge_item_definition",
        )
        url = self.get_set_monetary_components_url(self.facility, resource_category)
        data = []
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        resource_category.refresh_from_db()
        self.assertEqual(resource_category.configured_monetary_components, [])

    def test_set_monetary_components_with_multiple_components(self):
        self.client.force_authenticate(user=self.super_user)
        resource_category = self.create_resource_category(
            slug_value="charge-item",
            facility=self.facility,
            resource_type="charge_item_definition",
        )
        url = self.get_set_monetary_components_url(self.facility, resource_category)
        data = [
            {
                "monetary_component_type": "surcharge",
                "code": {"system": "http://example.com", "code": "surcharge-1"},
                "amount": "100.00",
            },
            {
                "monetary_component_type": "tax",
                "code": {"system": "http://example.com", "code": "tax-1"},
                "factor": "0.18",
            },
            {
                "monetary_component_type": "discount",
                "code": {"system": "http://example.com", "code": "discount-1"},
                "amount": "50.00",
            },
        ]
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        resource_category.refresh_from_db()
        self.assertEqual(len(resource_category.configured_monetary_components), 3)

    def test_set_monetary_components_with_duplicate_codes_rejected(self):
        self.client.force_authenticate(user=self.super_user)
        resource_category = self.create_resource_category(
            slug_value="charge-item",
            facility=self.facility,
            resource_type="charge_item_definition",
        )
        url = self.get_set_monetary_components_url(self.facility, resource_category)
        data = [
            {
                "monetary_component_type": "surcharge",
                "code": {"system": "http://example.com", "code": "same-code"},
                "amount": "100.00",
            },
            {
                "monetary_component_type": "tax",
                "code": {"system": "http://example.com", "code": "same-code"},
                "factor": "0.18",
            },
        ]
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 400)

    def test_set_monetary_components_overwrites_previous(self):
        self.client.force_authenticate(user=self.super_user)
        resource_category = self.create_resource_category(
            slug_value="charge-item",
            facility=self.facility,
            resource_type="charge_item_definition",
        )
        url = self.get_set_monetary_components_url(self.facility, resource_category)
        data = [
            {
                "monetary_component_type": "surcharge",
                "code": {"system": "http://example.com", "code": "surcharge-1"},
                "amount": "100.00",
            },
        ]
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        data = [
            {
                "monetary_component_type": "tax",
                "code": {"system": "http://example.com", "code": "tax-1"},
                "factor": "0.05",
            },
        ]
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        resource_category.refresh_from_db()
        self.assertEqual(len(resource_category.configured_monetary_components), 1)
        self.assertEqual(
            resource_category.configured_monetary_components[0][
                "monetary_component_type"
            ],
            "tax",
        )

    def test_create_resource_category_with_duplicate_slug(self):
        self.client.force_authenticate(user=self.super_user)
        self.create_resource_category(
            slug_value="test-resource-category", facility=self.facility
        )
        data = self.generate_resource_category_data(slug_value="test-resource-category")
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Resource category with this slug already exists.",
            status_code=400,
        )

    def test_delete_resource_category_as_super_user(self):
        self.client.force_authenticate(user=self.super_user)
        resource_category = self.create_resource_category(
            slug_value="test-category", facility=self.facility
        )
        url = self.get_detail_url(self.facility, resource_category)
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(
            ResourceCategory.objects.filter(id=resource_category.id).exists()
        )

    def test_delete_resource_category_as_regular_user_with_permission(self):
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        resource_category = self.create_resource_category(
            slug_value="test-category", facility=self.facility
        )
        url = self.get_detail_url(self.facility, resource_category)
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(
            ResourceCategory.objects.filter(id=resource_category.id).exists()
        )

    def test_delete_resource_category_as_regular_user_without_permission(self):
        self.client.force_authenticate(user=self.user)
        resource_category = self.create_resource_category(
            slug_value="test-category", facility=self.facility
        )
        url = self.get_detail_url(self.facility, resource_category)
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Access denied to resource category")
        self.assertTrue(
            ResourceCategory.objects.filter(id=resource_category.id).exists()
        )

    def test_delete_resource_category_with_associated_product_knowledge(self):
        self.client.force_authenticate(user=self.super_user)
        resource_category = self.create_resource_category(
            slug_value="test-category",
            facility=self.facility,
            resource_type="product_knowledge",
        )
        # Create a ProductKnowledge associated with the resource category
        baker.make(
            ProductKnowledge,
            facility=self.facility,
            name="Test Product",
            slug=self.calculate_slug("test-product", self.facility),
            category=resource_category,
        )
        url = self.get_detail_url(self.facility, resource_category)
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "Cannot delete a resource category associated with a resource",
        )

    def test_delete_resource_category_with_associated_activity_definition(self):
        self.client.force_authenticate(user=self.super_user)
        resource_category = self.create_resource_category(
            slug_value="test-category",
            facility=self.facility,
            resource_type="activity_definition",
        )
        # Create an ActivityDefinition associated with the resource category
        baker.make(
            ActivityDefinition,
            title="Test Activity",
            facility=self.facility,
            slug=self.calculate_slug("test-activity", self.facility),
            category=resource_category,
        )
        url = self.get_detail_url(self.facility, resource_category)
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "Cannot delete a resource category associated with a resource",
        )

    def test_delete_resource_category_with_associated_charge_item_definition(self):
        self.client.force_authenticate(user=self.super_user)
        resource_category = self.create_resource_category(
            slug_value="test-category",
            facility=self.facility,
            resource_type="charge_item_definition",
        )
        baker.make(
            ChargeItemDefinition,
            facility=self.facility,
            title="Test Charge Item",
            slug=self.calculate_slug("test-charge-item", self.facility),
            category=resource_category,
        )
        url = self.get_detail_url(self.facility, resource_category)
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "Cannot delete a resource category associated with a resource",
        )

    def test_delete_resource_category_with_children(self):
        self.client.force_authenticate(user=self.super_user)
        parent_category = self.create_resource_category(
            slug_value="parent-category",
            facility=self.facility,
            title="Parent Category",
        )
        self.create_resource_category(
            slug_value="child-category",
            facility=self.facility,
            title="Child Category",
            parent=parent_category,
        )
        url = self.get_detail_url(self.facility, parent_category)
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "Cannot delete a resource category with children",
        )
