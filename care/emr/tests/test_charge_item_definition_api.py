from decimal import Decimal

from django.db import IntegrityError
from django.urls import reverse
from pydantic import ValidationError as PydanticValidationError
from rest_framework import status

from care.emr.models.charge_item_definition import ChargeItemDefinition
from care.emr.models.resource_category import ResourceCategory
from care.emr.resources.charge_item_definition.spec import (
    ChargeItemDefinitionReadSpec,
    ChargeItemDefinitionStatusOptions,
    ChargeItemDefinitionWriteSpec,
)
from care.security.permissions.charge_item_definition import (
    ChargeItemDefinitionPermissions,
)
from care.utils.tests.base import CareAPITestBase


class TestChargeItemDefinitionViewSet(CareAPITestBase):
    """
    Test cases for checking ChargeItemDefinition CRUD operations

    Tests check if:
    1. Permissions are enforced for all operations
    2. Data validations work
    3. Proper responses are returned
    4. Filters work as expected
    5. Spec validations work correctly
    """

    def setUp(self):
        """Set up test data that's needed for all tests"""
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)

        # Create category for testing
        self.resource_category = ResourceCategory.objects.create(
            facility=self.facility,
            name="Test Category",
            slug="test-category",
            description="Test description",
        )

        self.base_url = reverse(
            "chargeitemdefinition-list",
            kwargs={"facility_external_id": self.facility.external_id},
        )

    def _get_detail_url(self, slug):
        """Helper to get the detail URL for a specific charge item definition."""
        return reverse(
            "chargeitemdefinition-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "slug": slug,
            },
        )

    def get_valid_charge_item_definition_data(self, **kwargs):
        """Helper to generate valid charge item definition data"""
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
                    "value": str(Decimal("100.00")),
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
        """Helper to create a charge item definition"""
        data = {
            "facility": self.facility,
            "status": ChargeItemDefinitionStatusOptions.active.value,
            "title": self.fake.sentence(nb_words=4),
            "slug": f"{self.facility.external_id}:{self.fake.slug()}",
            "description": self.fake.text(),
        }
        data.update(**kwargs)
        return ChargeItemDefinition.objects.create(**data)

    def test_list_charge_item_definition_without_permission(self):
        """Users without permission cannot list charge item definitions"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_charge_item_definition_with_permission(self):
        """Users with permission can list charge item definitions"""
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_read_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_charge_item_definition_without_permission(self):
        """Users without permission cannot create charge item definitions"""
        self.client.force_authenticate(user=self.user)
        data = self.get_valid_charge_item_definition_data()

        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_charge_item_definition_with_permission(self):
        """Users with permission can create charge item definitions"""
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
        """Test creating charge item definition with category"""
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
        """Test creating charge item definition with non-existent category"""
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_write_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        data = self.get_valid_charge_item_definition_data(category="non-existent-slug")
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_charge_item_definition_duplicate_slug(self):
        """Test creating charge item definition with duplicate slug"""
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_write_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        slug_value = "duplicate-slug"
        data = self.get_valid_charge_item_definition_data(slug_value=slug_value)

        # Create first definition
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Try to create second with same slug
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already exists", str(response.data))

    def test_create_charge_item_definition_duplicate_price_component_codes(self):
        """Test validation for duplicate codes in price components"""
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
                    "value": "100.00",
                    "code": {
                        "system": "http://test.system.com",
                        "code": "duplicate-code",
                        "display": "Test Code 1",
                    },
                },
                {
                    "monetary_component_type": "base",
                    "currency": "INR",
                    "value": "200.00",
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
        """Test creating charge item definition with empty price components"""
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_write_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        data = self.get_valid_charge_item_definition_data(price_components=[])
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_charge_item_definition_invalid_status(self):
        """Test validation for invalid status"""
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_write_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        data = self.get_valid_charge_item_definition_data(status="invalid_status")
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_charge_item_definition_missing_required_fields(self):
        """Test validation for missing required fields"""
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_write_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        # Test missing title
        data = self.get_valid_charge_item_definition_data()
        del data["title"]
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Test missing status
        data = self.get_valid_charge_item_definition_data()
        del data["status"]
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Test missing slug_value
        data = self.get_valid_charge_item_definition_data()
        del data["slug_value"]
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_charge_item_definition_with_permission(self):
        """Test updating charge item definition with permission"""
        role = self.create_role_with_permissions(
            [
                ChargeItemDefinitionPermissions.can_write_charge_item_definition.name,
                ChargeItemDefinitionPermissions.can_read_charge_item_definition.name,
            ]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        # Create charge item definition first
        charge_def = self.create_charge_item_definition()
        url = self._get_detail_url(charge_def.slug)

        data = self.get_valid_charge_item_definition_data(
            title="Updated Title",
            slug_value=charge_def.slug.split(":", 1)[
                1
            ],  # Extract slug part after facility
        )
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Updated Title")

    def test_update_charge_item_definition_without_permission(self):
        """Test updating charge item definition without permission"""
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
        """Test retrieving charge item definition with permission"""
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
        """Test retrieving charge item definition without permission"""
        self.client.force_authenticate(user=self.user)

        charge_def = self.create_charge_item_definition()
        url = self._get_detail_url(charge_def.slug)

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_by_status(self):
        """Test filtering charge item definitions by status"""
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_read_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        # Create definitions with different statuses
        self.create_charge_item_definition(
            status=ChargeItemDefinitionStatusOptions.active.value,
            title="Active Definition",
        )
        self.create_charge_item_definition(
            status=ChargeItemDefinitionStatusOptions.draft.value,
            title="Draft Definition",
        )

        # Filter by status
        response = self.client.get(f"{self.base_url}?status=active")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["title"], "Active Definition")

    def test_filter_by_title(self):
        """Test filtering charge item definitions by title"""
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_read_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        # Create definitions with different titles
        self.create_charge_item_definition(title="Blood Test Definition")
        self.create_charge_item_definition(title="X-Ray Definition")

        # Filter by title
        response = self.client.get(f"{self.base_url}?title=blood")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertTrue("Blood Test" in response.data["results"][0]["title"])

    def test_filter_by_category(self):
        """Test filtering charge item definitions by category"""
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_read_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        # Create definitions with and without category
        self.create_charge_item_definition(
            title="With Category", category=self.resource_category
        )
        self.create_charge_item_definition(title="Without Category")

        # Filter by category
        response = self.client.get(
            f"{self.base_url}?category={self.resource_category.slug}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["title"], "With Category")

    def test_ordering_by_created_date(self):
        """Test ordering charge item definitions by created date"""
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_read_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        # Create definitions
        self.create_charge_item_definition(title="First Definition")
        self.create_charge_item_definition(title="Second Definition")

        # Test ascending order
        response = self.client.get(f"{self.base_url}?ordering=created_date")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

        # Test descending order
        response = self.client.get(f"{self.base_url}?ordering=-created_date")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

    def test_upsert_charge_item_definition(self):
        """Test upserting charge item definition"""
        role = self.create_role_with_permissions(
            [ChargeItemDefinitionPermissions.can_write_charge_item_definition.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        data = self.get_valid_charge_item_definition_data()

        # First upsert should create
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        first_id = response.data["id"]

        # Second upsert with same slug should update
        data["title"] = "Updated Title"
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], first_id)  # Same ID means update
        self.assertEqual(response.data["title"], "Updated Title")


class TestChargeItemDefinitionModelValidation(CareAPITestBase):
    """
    Test cases for ChargeItemDefinition model-level validations

    Tests cover:
    1. Model field validations
    2. Database constraints
    3. Business logic validations
    """

    def setUp(self):
        """Set up test data"""
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)

    def test_charge_item_definition_model_validation(self):
        """Test ChargeItemDefinition model field validations"""
        # Test creating with valid data
        definition = ChargeItemDefinition.objects.create(
            facility=self.facility,
            status=ChargeItemDefinitionStatusOptions.active.value,
            title="Test Definition",
            slug=f"{self.facility.external_id}:test-def",
        )
        self.assertIsNotNone(definition.id)

    def test_charge_item_definition_slug_uniqueness(self):
        """Test that slug must be unique"""
        slug = f"{self.facility.external_id}:unique-slug"

        # Create first definition
        ChargeItemDefinition.objects.create(
            facility=self.facility,
            status=ChargeItemDefinitionStatusOptions.active.value,
            title="First Definition",
            slug=slug,
        )

        # Try to create second with same slug - should fail
        with self.assertRaises(IntegrityError):
            ChargeItemDefinition.objects.create(
                facility=self.facility,
                status=ChargeItemDefinitionStatusOptions.active.value,
                title="Second Definition",
                slug=slug,
            )


class TestChargeItemDefinitionSpecValidation(CareAPITestBase):
    """
    Test cases for ChargeItemDefinition Pydantic spec validations

    Tests cover:
    1. Pydantic field validations
    2. Custom model validators
    3. Spec-specific business rules
    """

    def setUp(self):
        """Set up test data"""
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)

    def get_valid_monetary_component(self, component_type="base", **kwargs):
        """Helper to create valid monetary component"""
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
        """Test ChargeItemDefinitionWriteSpec validations"""
        # Valid spec should pass
        valid_data = {
            "status": ChargeItemDefinitionStatusOptions.active.value,
            "title": "Test Definition",
            "slug_value": "test-def",
            "price_components": [self.get_valid_monetary_component()],
        }
        spec = ChargeItemDefinitionWriteSpec(**valid_data)
        self.assertEqual(spec.title, "Test Definition")

    def test_charge_item_definition_spec_invalid_status(self):
        """Test invalid status validation"""
        with self.assertRaises(PydanticValidationError):
            ChargeItemDefinitionWriteSpec(
                status="invalid_status",
                title="Test Definition",
                slug_value="test-def",
                price_components=[],
            )

    def test_charge_item_definition_spec_duplicate_price_components(self):
        """Test duplicate price component codes validation"""
        with self.assertRaises(PydanticValidationError) as context:
            ChargeItemDefinitionWriteSpec(
                status=ChargeItemDefinitionStatusOptions.active.value,
                title="Test Definition",
                slug_value="test-def",
                price_components=[
                    self.get_valid_monetary_component("base"),
                    self.get_valid_monetary_component("base"),  # Same code
                ],
            )
        self.assertIn("Same codes", str(context.exception))

    def test_charge_item_definition_read_spec_serialization(self):
        """Test ChargeItemDefinitionReadSpec serialization"""
        # Create a charge item definition
        definition = ChargeItemDefinition.objects.create(
            facility=self.facility,
            status=ChargeItemDefinitionStatusOptions.active.value,
            title="Test Definition",
            slug=f"{self.facility.external_id}:test-def",
            price_components=[],
        )

        # Serialize using read spec
        serialized = ChargeItemDefinitionReadSpec.serialize(definition)
        self.assertEqual(serialized.title, "Test Definition")
        self.assertEqual(serialized.id, definition.external_id)

    def test_charge_item_definition_read_spec_with_category(self):
        """Test ChargeItemDefinitionReadSpec serialization with category"""
        # Create category
        category = ResourceCategory.objects.create(
            facility=self.facility, name="Test Category", slug="test-category"
        )

        # Create definition with category
        definition = ChargeItemDefinition.objects.create(
            facility=self.facility,
            status=ChargeItemDefinitionStatusOptions.active.value,
            title="Test Definition",
            slug=f"{self.facility.external_id}:test-def",
            price_components=[],
            category=category,
        )

        # Serialize using read spec
        serialized = ChargeItemDefinitionReadSpec.serialize(definition)
        self.assertIsNotNone(serialized.category)

    def test_charge_item_definition_status_options(self):
        """Test all charge item definition status options"""
        for status_option in ChargeItemDefinitionStatusOptions:
            spec_data = {
                "status": status_option.value,
                "title": f"Test Definition {status_option.value}",
                "slug_value": f"test-def-{status_option.value}",
                "price_components": [],
            }
            spec = ChargeItemDefinitionWriteSpec(**spec_data)
            self.assertEqual(spec.status, status_option.value)
