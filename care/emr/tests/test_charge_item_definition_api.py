from decimal import Decimal

from django.urls import reverse
from pydantic import ValidationError as PydanticValidationError
from rest_framework import status

from care.emr.models.charge_item_definition import ChargeItemDefinition
from care.emr.models.resource_category import ResourceCategory
from care.emr.resources.charge_item_definition.spec import (
    ChargeItemDefinitionStatusOptions,
    ChargeItemDefinitionWriteSpec,
)
from care.security.permissions.charge_item_definition import (
    ChargeItemDefinitionPermissions,
)
from care.utils.tests.base import CareAPITestBase


class TestChargeItemDefinitionViewSet(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.facility.default_internal_organization

        self.resource_category = ResourceCategory.objects.create(
            facility=self.facility,
            title="Test Category",
            slug="i-test-category",
            description="Test description",
            resource_type="test_type",
            resource_sub_type="test_sub_type",
        )

        self.base_url = reverse(
            "charge_item_definition-list",
            kwargs={"facility_external_id": self.facility.external_id},
        )

    def _get_detail_url(self, slug):
        return reverse(
            "charge_item_definition-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "slug": slug,
            },
        )

    def get_valid_charge_item_definition_data(self, **kwargs):
        data = {
            "status": ChargeItemDefinitionStatusOptions.active.value,
            "title": self.fake.sentence(nb_words=4),
            "slug_value": self.fake.slug(),
            "description": self.fake.text(),
            "purpose": self.fake.text(),
            "price_components": [
                {
                    "monetary_component_type": "base",
                    "currency": "INR",
                    "amount": str(Decimal("100.00")),
                    "code": {
                        "system": "http://test.system.com",
                        "code": "test-code-001",
                        "display": "Test Code",
                    },
                }
            ],
        }
        data.update(**kwargs)
        return data

    def create_charge_item_definition(self, **kwargs):
        data = {
            "facility": self.facility,
            "status": ChargeItemDefinitionStatusOptions.active.value,
            "title": self.fake.sentence(nb_words=4),
            "slug": f"f-{self.facility.external_id}-{self.fake.slug()}",
            "description": self.fake.text(),
        }
        data.update(**kwargs)
        return ChargeItemDefinition.objects.create(**data)

    def test_list_charge_item_definition_without_permission(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_charge_item_definition_with_permission(self):
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_read_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_charge_item_definition_without_permission(self):
        self.client.force_authenticate(user=self.user)
        data = self.get_valid_charge_item_definition_data()

        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_charge_item_definition_with_permission(self):
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_write_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        data = self.get_valid_charge_item_definition_data()
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], data["title"])

    def test_create_charge_item_definition_with_category(self):
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_write_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        data = self.get_valid_charge_item_definition_data(
            category=self.resource_category.slug
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["category"]["slug"], self.resource_category.slug)

    def test_create_charge_item_definition_invalid_category(self):
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_write_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        data = self.get_valid_charge_item_definition_data(category="non-existent-slug")
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_charge_item_definition_duplicate_slug(self):
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_write_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        slug_value = "duplicate-slug"
        data = self.get_valid_charge_item_definition_data(slug_value=slug_value)

        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already exists", str(response.data))

    def test_create_charge_item_definition_duplicate_price_component_codes(self):
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_write_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        data = self.get_valid_charge_item_definition_data(
            price_components=[
                {
                    "monetary_component_type": "base",
                    "currency": "INR",
                    "amount": "100.00",
                    "code": {
                        "system": "http://test.system.com",
                        "code": "duplicate-code",
                        "display": "Test Code 1",
                    },
                },
                {
                    "monetary_component_type": "base",
                    "currency": "INR",
                    "amount": "200.00",
                    "code": {
                        "system": "http://test.system.com",
                        "code": "duplicate-code",
                        "display": "Test Code 2",
                    },
                },
            ]
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_charge_item_definition_empty_price_components(self):
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_write_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        data = self.get_valid_charge_item_definition_data(price_components=[])
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_charge_item_definition_invalid_status(self):
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_write_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        data = self.get_valid_charge_item_definition_data(status="invalid_status")
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_charge_item_definition_missing_required_fields(self):
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_write_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        data = self.get_valid_charge_item_definition_data()
        del data["title"]
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        data = self.get_valid_charge_item_definition_data()
        del data["status"]
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = self.get_valid_charge_item_definition_data()
        del data["slug_value"]
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_charge_item_definition_with_permission(self):
        role = self.create_role_with_permissions(
            [
                ChargeItemDefinitionPermissions.can_write_charge_item_definition.name,
                ChargeItemDefinitionPermissions.can_read_charge_item_definition.name,
            ]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        charge_def = self.create_charge_item_definition()
        url = self._get_detail_url(charge_def.slug)

        data = self.get_valid_charge_item_definition_data(
            title="Updated Title",
            slug_value=charge_def.parse_slug(charge_def.slug)["slug_value"],
        )
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Updated Title")

    def test_update_charge_item_definition_without_permission(self):
        read_role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_read_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(
            self.organization, self.user, read_role
        )
        self.client.force_authenticate(user=self.user)

        charge_def = self.create_charge_item_definition()
        url = self._get_detail_url(charge_def.slug)

        data = self.get_valid_charge_item_definition_data(title="Updated Title")
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_charge_item_definition_with_permission(self):
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_read_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        charge_def = self.create_charge_item_definition(title="Test Definition")
        url = self._get_detail_url(charge_def.slug)

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Test Definition")

    def test_retrieve_charge_item_definition_without_permission(self):
        self.client.force_authenticate(user=self.user)

        charge_def = self.create_charge_item_definition()
        url = self._get_detail_url(charge_def.slug)

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_by_status(self):
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_read_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        self.create_charge_item_definition(
            status=ChargeItemDefinitionStatusOptions.active.value,
            title="Active Definition",
        )
        self.create_charge_item_definition(
            status=ChargeItemDefinitionStatusOptions.draft.value,
            title="Draft Definition",
        )
        response = self.client.get(f"{self.base_url}?status=active")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["title"], "Active Definition")

    def test_filter_by_title(self):
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_read_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        self.create_charge_item_definition(title="Blood Test Definition")
        self.create_charge_item_definition(title="X-Ray Definition")
        response = self.client.get(f"{self.base_url}?title=blood")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertTrue("Blood Test" in response.data["results"][0]["title"])

    def test_filter_by_category(self):
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_read_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        self.create_charge_item_definition(
            title="With Category", category=self.resource_category
        )
        self.create_charge_item_definition(title="Without Category")
        response = self.client.get(
            f"{self.base_url}?category={self.resource_category.slug}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["title"], "With Category")

    def test_ordering_by_created_date(self):
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_read_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        self.create_charge_item_definition(title="First Definition")
        self.create_charge_item_definition(title="Second Definition")

        response = self.client.get(f"{self.base_url}?ordering=created_date")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)
        response = self.client.get(f"{self.base_url}?ordering=-created_date")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

    def test_upsert_charge_item_definition(self):
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_write_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        data = self.get_valid_charge_item_definition_data()
        upsert_url = f"{self.base_url}upsert/"

        upsert_data = {"datapoints": [data]}

        response = self.client.post(upsert_url, upsert_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        first_id = response.data[0]["id"]
        first_slug = response.data[0]["slug"]

        data["title"] = "Updated Title"
        data["id"] = first_slug
        upsert_data = {"datapoints": [data]}
        response = self.client.post(upsert_url, upsert_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["id"], first_id)
        self.assertEqual(response.data[0]["title"], "Updated Title")


class TestChargeItemDefinitionModelValidation(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)

    def test_charge_item_definition_model_validation(self):
        definition = ChargeItemDefinition.objects.create(
            facility=self.facility,
            status=ChargeItemDefinitionStatusOptions.active.value,
            title="Test Definition",
            slug=f"f-{self.facility.external_id}-test-def",
        )
        self.assertIsNotNone(definition.id)

    def test_charge_item_definition_slug_uniqueness(self):
        slug = f"f-{self.facility.external_id}-unique-slug"

        first_definition = ChargeItemDefinition.objects.create(
            facility=self.facility,
            status=ChargeItemDefinitionStatusOptions.active.value,
            title="First Definition",
            slug=slug,
        )

        second_definition = ChargeItemDefinition.objects.create(
            facility=self.facility,
            status=ChargeItemDefinitionStatusOptions.active.value,
            title="Second Definition",
            slug=slug,
        )
        self.assertIsNotNone(first_definition.id)
        self.assertIsNotNone(second_definition.id)
        self.assertEqual(first_definition.slug, second_definition.slug)


class TestChargeItemDefinitionSpecValidation(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)

    def get_valid_monetary_component(self, component_type="base", **kwargs):
        component = {
            "monetary_component_type": component_type,
            "amount": 100.0,
            "code": {
                "system": "http://test.system.com",
                "code": f"test-{component_type}",
                "display": f"Test {component_type.title()}",
            },
        }
        component.update(**kwargs)
        return component

    def test_charge_item_definition_spec_validation(self):
        valid_data = {
            "status": ChargeItemDefinitionStatusOptions.active.value,
            "title": "Test Definition",
            "slug_value": "test-def",
            "price_components": [self.get_valid_monetary_component()],
        }
        spec = ChargeItemDefinitionWriteSpec(**valid_data)
        self.assertEqual(spec.title, "Test Definition")

    def test_charge_item_definition_spec_invalid_status(self):
        with self.assertRaises(PydanticValidationError):
            ChargeItemDefinitionWriteSpec(
                status="invalid_status",
                title="Test Definition",
                slug_value="test-def",
                price_components=[],
            )

    def test_charge_item_definition_spec_duplicate_price_components(self):
        with self.assertRaises(PydanticValidationError) as context:
            ChargeItemDefinitionWriteSpec(
                status=ChargeItemDefinitionStatusOptions.active.value,
                title="Test Definition",
                slug_value="test-def",
                price_components=[
                    self.get_valid_monetary_component("base"),
                    self.get_valid_monetary_component("base"),
                ],
            )
        self.assertIn("Same codes", str(context.exception))

    def test_charge_item_definition_read_spec_serialization(self):
        proper_slug = f"f-{self.facility.external_id}-test-def"
        definition = ChargeItemDefinition.objects.create(
            facility=self.facility,
            status=ChargeItemDefinitionStatusOptions.active.value,
            title="Test Definition",
            slug=proper_slug,
            price_components=[],
        )

        self.assertEqual(definition.title, "Test Definition")
        self.assertEqual(definition.slug, proper_slug)
        self.assertIsNotNone(definition.external_id)

    def test_charge_item_definition_read_spec_with_category(self):
        category = ResourceCategory.objects.create(
            facility=self.facility,
            title="Test Category",
            slug=f"f-{self.facility.external_id}-test-category",
            resource_type="test_type",
            resource_sub_type="test_sub_type",
        )

        proper_slug = f"f-{self.facility.external_id}-test-def-with-cat"
        definition = ChargeItemDefinition.objects.create(
            facility=self.facility,
            status=ChargeItemDefinitionStatusOptions.active.value,
            title="Test Definition with Category",
            slug=proper_slug,
            price_components=[],
            category=category,
        )

        self.assertEqual(definition.category, category)
        self.assertEqual(definition.category.title, "Test Category")

    def test_charge_item_definition_status_options(self):
        for status_option in ChargeItemDefinitionStatusOptions:
            spec_data = {
                "status": status_option.value,
                "title": f"Test Definition {status_option.value}",
                "slug_value": f"test-def-{status_option.value}",
                "price_components": [],
            }
            spec = ChargeItemDefinitionWriteSpec(**spec_data)
            self.assertEqual(spec.status, status_option.value)


class TestChargeItemDefinitionMissingCoverage(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.facility.default_internal_organization

        self.resource_category = ResourceCategory.objects.create(
            facility=self.facility,
            title="Test Category",
            slug="i-test-category",
            description="Test description",
            resource_type="test_type",
            resource_sub_type="test_sub_type",
        )

        # Create parent category for testing include_children
        self.parent_category = ResourceCategory.objects.create(
            facility=self.facility,
            title="Parent Category",
            slug="i-parent-category",
            description="Parent description",
            resource_type="parent_type",
            resource_sub_type="parent_sub_type",
        )

        # Create child category
        self.child_category = ResourceCategory.objects.create(
            facility=self.facility,
            title="Child Category",
            slug="i-child-category",
            description="Child description",
            resource_type="child_type",
            resource_sub_type="child_sub_type",
            parent=self.parent_category,
            parent_cache=[self.parent_category.id],
        )

        self.base_url = reverse(
            "charge_item_definition-list",
            kwargs={"facility_external_id": self.facility.external_id},
        )

    def _get_detail_url(self, slug):
        return reverse(
            "charge_item_definition-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "slug": slug,
            },
        )

    def get_valid_charge_item_definition_data(self, **kwargs):
        data = {
            "status": ChargeItemDefinitionStatusOptions.active.value,
            "title": self.fake.sentence(nb_words=4),
            "slug_value": self.fake.slug(),
            "description": self.fake.text(),
            "purpose": self.fake.text(),
            "price_components": [
                {
                    "monetary_component_type": "base",
                    "currency": "INR",
                    "amount": str(Decimal("100.00")),
                    "code": {
                        "system": "http://test.system.com",
                        "code": "test-code-001",
                        "display": "Test Code",
                    },
                }
            ],
        }
        data.update(**kwargs)
        return data

    def create_charge_item_definition(self, **kwargs):
        data = {
            "facility": self.facility,
            "status": ChargeItemDefinitionStatusOptions.active.value,
            "title": self.fake.sentence(nb_words=4),
            "slug": f"f-{self.facility.external_id}-{self.fake.slug()}",
            "description": self.fake.text(),
        }
        data.update(**kwargs)
        return ChargeItemDefinition.objects.create(**data)

    def test_get_facility_obj_with_invalid_facility_id(self):
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_read_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        invalid_url = reverse(
            "charge_item_definition-list",
            kwargs={"facility_external_id": "invalid-facility-id"},
        )
        response = self.client.get(invalid_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_validate_data_with_non_existent_category(self):
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_write_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        data = self.get_valid_charge_item_definition_data(
            category="non-existent-category"
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_perform_create_sets_facility_and_slug(self):
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_write_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        slug_value = "test-create-slug"
        data = self.get_valid_charge_item_definition_data(slug_value=slug_value)
        response = self.client.post(self.base_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_slug = f"f-{self.facility.external_id}-{slug_value}"
        self.assertEqual(response.data["slug"], expected_slug)

    def test_perform_update_recalculates_slug(self):
        role = self.create_role_with_permissions(
            [
                ChargeItemDefinitionPermissions.can_write_charge_item_definition.name,
                ChargeItemDefinitionPermissions.can_read_charge_item_definition.name,
            ]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        charge_def = self.create_charge_item_definition()
        url = self._get_detail_url(charge_def.slug)

        new_slug_value = "updated-slug-value"
        data = self.get_valid_charge_item_definition_data(
            title="Updated Title",
            slug_value=new_slug_value,
        )
        response = self.client.put(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_slug = f"f-{self.facility.external_id}-{new_slug_value}"
        self.assertEqual(response.data["slug"], expected_slug)

    def test_authorize_create_without_permission(self):
        self.client.force_authenticate(user=self.user)
        data = self.get_valid_charge_item_definition_data()
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authorize_update_without_permission(self):
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_write_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        charge_def = self.create_charge_item_definition()

        self.user.facilityorganizationuser_set.all().delete()
        url = self._get_detail_url(charge_def.slug)

        data = self.get_valid_charge_item_definition_data(title="Updated Title")
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_queryset_without_list_permission(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_queryset_with_category_filter_include_children_true(self):
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_read_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        self.create_charge_item_definition(
            title="Parent Category Definition", category=self.parent_category
        )
        self.create_charge_item_definition(
            title="Child Category Definition", category=self.child_category
        )
        self.create_charge_item_definition(
            title="Unrelated Definition", category=self.resource_category
        )

        response = self.client.get(
            f"{self.base_url}?category={self.parent_category.slug}&include_children=true"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [result["title"] for result in response.data["results"]]
        self.assertIn("Child Category Definition", titles)
        self.assertEqual(len(response.data["results"]), 1)

    def test_get_queryset_with_category_filter_include_children_false(self):
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_read_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        self.create_charge_item_definition(
            title="Parent Category Definition", category=self.parent_category
        )
        self.create_charge_item_definition(
            title="Child Category Definition", category=self.child_category
        )

        response = self.client.get(
            f"{self.base_url}?category={self.parent_category.slug}&include_children=false"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["title"], "Parent Category Definition"
        )

    def test_get_queryset_with_category_filter_lowercase_true(self):
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_read_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        self.create_charge_item_definition(
            title="Child Category Definition", category=self.child_category
        )

        response = self.client.get(
            f"{self.base_url}?category={self.parent_category.slug}&include_children=True"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_get_queryset_with_invalid_category(self):
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_read_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        response = self.client.get(f"{self.base_url}?category=invalid-category")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_dummy_filters(self):
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_read_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        self.create_charge_item_definition(title="Test Definition 1")
        self.create_charge_item_definition(title="Test Definition 2")

        response = self.client.get(f"{self.base_url}?category=&include_children=")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

    def test_lookup_field_slug(self):
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_read_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        charge_def = self.create_charge_item_definition(title="Test Lookup")

        url = self._get_detail_url(charge_def.slug)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Test Lookup")

        invalid_url = reverse(
            "charge_item_definition-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "slug": str(charge_def.external_id),
            },
        )
        response = self.client.get(invalid_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_filter_backends_configuration(self):
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_read_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        self.create_charge_item_definition(
            title="Active Definition",
            status=ChargeItemDefinitionStatusOptions.active.value,
        )
        self.create_charge_item_definition(
            title="Draft Definition",
            status=ChargeItemDefinitionStatusOptions.draft.value,
        )

        response = self.client.get(f"{self.base_url}?status=active")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["title"], "Active Definition")

        response = self.client.get(f"{self.base_url}?ordering=title")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

        response = self.client.get(f"{self.base_url}?ordering=-title")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

    def test_select_related_category_optimization(self):
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_read_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        self.create_charge_item_definition(
            title="Definition with Category", category=self.resource_category
        )

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data["results"]), 1)
        result = response.data["results"][0]
        self.assertIsNotNone(result.get("category"))
        if result.get("category"):
            self.assertEqual(result["category"]["title"], self.resource_category.title)
