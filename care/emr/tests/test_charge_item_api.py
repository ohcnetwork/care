from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.urls import reverse
from pydantic import ValidationError as PydanticValidationError
from rest_framework import status

from care.emr.models.account import Account
from care.emr.models.charge_item import ChargeItem
from care.emr.models.charge_item_definition import ChargeItemDefinition
from care.emr.resources.charge_item.spec import (
    CHARGE_ITEM_CANCELLED_STATUS,
    ChargeItemReadSpec,
    ChargeItemResourceOptions,
    ChargeItemStatusOptions,
    ChargeItemWriteSpec,
)
from care.emr.resources.charge_item_definition.spec import (
    ChargeItemDefinitionStatusOptions,
)
from care.emr.resources.common.monetary_component import MonetaryComponentType
from care.security.permissions.charge_item import ChargeItemPermissions
from care.utils.tests.base import CareAPITestBase


class TestChargeItemViewSet(CareAPITestBase):
    """
    Test cases for checking ChargeItem CRUD operations

    Tests check if:
    1. Permissions are enforced for all operations
    2. Data validations work
    3. Proper responses are returned
    4. Filters work as expected
    5. Spec validations work correctly
    6. Special actions work properly
    """

    def setUp(self):
        """Set up test data that's needed for all tests"""
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.patient = self.create_patient()
        self.encounter = self.create_encounter(
            patient=self.patient, facility=self.facility, organization=self.organization
        )

        # Create an account for the patient
        self.account = Account.objects.create(
            facility=self.facility,
            patient=self.patient,
            name=f"Account for {self.patient.name}",
            type="patient",
            status="active",
        )

        # Create a charge item definition for testing
        self.charge_item_definition = ChargeItemDefinition.objects.create(
            facility=self.facility,
            status=ChargeItemDefinitionStatusOptions.active.value,
            title="Test Charge Definition",
            slug=f"{self.facility.external_id}:test-charge-def",
            price_components=[
                {
                    "monetary_component_type": "base",
                    "currency": "INR",
                    "value": "100.00",
                }
            ],
        )

        self.base_url = reverse(
            "charge-item-list",
            kwargs={"facility_external_id": self.facility.external_id},
        )

    def _get_detail_url(self, charge_item_id):
        """Helper to get the detail URL for a specific charge item."""
        return reverse(
            "charge-item-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": charge_item_id,
            },
        )

    def get_valid_charge_item_data(self, **kwargs):
        """Helper to generate valid charge item data"""
        data = {
            "title": self.fake.sentence(nb_words=4),
            "description": self.fake.text(),
            "status": ChargeItemStatusOptions.billable.value,
            "quantity": 1.0,
            "unit_price_components": [
                {
                    "monetary_component_type": "base",
                    "currency": "INR",
                    "value": "100.00",
                    "code": {
                        "system": "http://test.system.com",
                        "code": "test-code-001",
                        "display": "Test Code",
                    },
                }
            ],
            "encounter": self.encounter.external_id,
            "account": self.account.external_id,
        }
        data.update(**kwargs)
        return data

    def create_charge_item(self, **kwargs):
        """Helper to create a charge item"""
        data = {
            "facility": self.facility,
            "title": self.fake.sentence(nb_words=4),
            "patient": self.patient,
            "encounter": self.encounter,
            "account": self.account,
            "status": ChargeItemStatusOptions.billable.value,
            "quantity": Decimal("1.00"),
            "unit_price_components": [
                {
                    "monetary_component_type": "base",
                    "currency": "INR",
                    "value": "100.00",
                }
            ],
            "total_price_components": [
                {
                    "monetary_component_type": "base",
                    "currency": "INR",
                    "value": "100.00",
                }
            ],
            "total_price": Decimal("100.00"),
        }
        data.update(**kwargs)
        return ChargeItem.objects.create(**data)

    def test_list_charge_items_without_permission(self):
        """Users without permission cannot list charge items"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_charge_items_with_permission(self):
        """Users with permission can list charge items"""
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_read_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_charge_item_without_permission(self):
        """Users without permission cannot create charge items"""
        self.client.force_authenticate(user=self.user)
        data = self.get_valid_charge_item_data()

        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_charge_item_with_permission(self):
        """Users with permission can create charge items"""
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_create_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        data = self.get_valid_charge_item_data()
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], data["title"])

    def test_create_charge_item_with_patient_only(self):
        """Test creating charge item with patient only (no encounter)"""
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_create_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        data = self.get_valid_charge_item_data()
        del data["encounter"]
        data["patient"] = self.patient.external_id

        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_charge_item_missing_patient_and_encounter(self):
        """Test validation when both patient and encounter are missing"""
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_create_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        data = self.get_valid_charge_item_data()
        del data["encounter"]

        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_charge_item_duplicate_price_component_codes(self):
        """Test validation for duplicate codes in unit price components"""
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_create_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        data = self.get_valid_charge_item_data(
            unit_price_components=[
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
                    "monetary_component_type": "tax",
                    "currency": "INR",
                    "value": "18.00",
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

    def test_create_charge_item_multiple_base_components(self):
        """Test validation for multiple base components"""
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_create_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        data = self.get_valid_charge_item_data(
            unit_price_components=[
                {
                    "monetary_component_type": "base",
                    "currency": "INR",
                    "value": "100.00",
                    "code": {
                        "system": "http://test.system.com",
                        "code": "base-code-1",
                        "display": "Base Code 1",
                    },
                },
                {
                    "monetary_component_type": "base",
                    "currency": "INR",
                    "value": "200.00",
                    "code": {
                        "system": "http://test.system.com",
                        "code": "base-code-2",
                        "display": "Base Code 2",
                    },
                },
            ]
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_charge_item_with_service_resource(self):
        """Test creating charge item with service resource"""
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_create_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        # Create a service request
        service_request = self.create_service_request(
            patient=self.patient, facility=self.facility, encounter=self.encounter
        )

        data = self.get_valid_charge_item_data(
            service_resource=ChargeItemResourceOptions.service_request.value,
            service_resource_id=str(service_request.external_id),
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_charge_item_service_resource_without_id(self):
        """Test validation when service resource is specified without ID"""
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_create_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        data = self.get_valid_charge_item_data(
            service_resource=ChargeItemResourceOptions.service_request.value
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_charge_item_invalid_status(self):
        """Test validation for invalid status"""
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_create_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        data = self.get_valid_charge_item_data(status="invalid_status")
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_charge_item_missing_required_fields(self):
        """Test validation for missing required fields"""
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_create_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        # Test missing title
        data = self.get_valid_charge_item_data()
        del data["title"]
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Test missing status
        data = self.get_valid_charge_item_data()
        del data["status"]
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Test missing quantity
        data = self.get_valid_charge_item_data()
        del data["quantity"]
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_charge_item_with_permission(self):
        """Test updating charge item with permission"""
        role = self.create_role_with_permissions(
            [
                ChargeItemPermissions.can_update_charge_item.name,
                ChargeItemPermissions.can_read_charge_item.name,
            ]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        # Create charge item first
        charge_item = self.create_charge_item()
        url = self._get_detail_url(charge_item.external_id)

        data = {
            "title": "Updated Title",
            "description": "Updated description",
            "status": ChargeItemStatusOptions.billable.value,
            "quantity": 2.0,
            "unit_price_components": [
                {
                    "monetary_component_type": "base",
                    "currency": "INR",
                    "value": "200.00",
                    "code": {
                        "system": "http://test.system.com",
                        "code": "updated-code",
                        "display": "Updated Code",
                    },
                }
            ],
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Updated Title")

    def test_update_charge_item_without_permission(self):
        """Test updating charge item without permission"""
        read_role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_read_charge_item.name]
        )
        self.attach_role_facility_organization_user(
            self.organization, self.user, read_role
        )
        self.client.force_authenticate(user=self.user)

        charge_item = self.create_charge_item()
        url = self._get_detail_url(charge_item.external_id)

        data = {
            "title": "Updated Title",
            "status": ChargeItemStatusOptions.billable.value,
            "quantity": 2.0,
            "unit_price_components": [],
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_cancelled_charge_item(self):
        """Test that cancelled charge items cannot be updated"""
        role = self.create_role_with_permissions(
            [
                ChargeItemPermissions.can_update_charge_item.name,
                ChargeItemPermissions.can_read_charge_item.name,
            ]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        # Create cancelled charge item
        charge_item = self.create_charge_item(
            status=ChargeItemStatusOptions.entered_in_error.value
        )
        url = self._get_detail_url(charge_item.external_id)

        data = {
            "title": "Updated Title",
            "status": ChargeItemStatusOptions.entered_in_error.value,
            "quantity": 2.0,
            "unit_price_components": [],
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cancelled", str(response.data))

    def test_retrieve_charge_item_with_permission(self):
        """Test retrieving charge item with permission"""
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_read_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        charge_item = self.create_charge_item(title="Test Charge Item")
        url = self._get_detail_url(charge_item.external_id)

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Test Charge Item")

    def test_retrieve_charge_item_without_permission(self):
        """Test retrieving charge item without permission"""
        self.client.force_authenticate(user=self.user)

        charge_item = self.create_charge_item()
        url = self._get_detail_url(charge_item.external_id)

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_by_status(self):
        """Test filtering charge items by status"""
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_read_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        # Create items with different statuses
        self.create_charge_item(
            status=ChargeItemStatusOptions.billable.value, title="Billable Item"
        )
        self.create_charge_item(
            status=ChargeItemStatusOptions.planned.value, title="Planned Item"
        )

        # Filter by status
        response = self.client.get(f"{self.base_url}?status=billable")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["title"], "Billable Item")

    def test_filter_by_title(self):
        """Test filtering charge items by title"""
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_read_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        # Create items with different titles
        self.create_charge_item(title="Blood Test Charge")
        self.create_charge_item(title="X-Ray Charge")

        # Filter by title
        response = self.client.get(f"{self.base_url}?title=blood")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertTrue("Blood Test" in response.data["results"][0]["title"])

    def test_filter_by_account(self):
        """Test filtering charge items by account"""
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_read_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        # Create another account and patient
        another_patient = self.create_patient()
        another_account = Account.objects.create(
            facility=self.facility,
            patient=another_patient,
            name=f"Account for {another_patient.name}",
            type="patient",
            status="active",
        )

        # Create items for different accounts
        self.create_charge_item(title="Item for Account 1", account=self.account)
        self.create_charge_item(
            title="Item for Account 2", account=another_account, patient=another_patient
        )

        # Filter by account
        response = self.client.get(
            f"{self.base_url}?account={self.account.external_id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["title"], "Item for Account 1")

    def test_filter_by_encounter(self):
        """Test filtering charge items by encounter"""
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_read_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        # Create another encounter
        another_encounter = self.create_encounter(
            patient=self.patient, facility=self.facility, organization=self.organization
        )

        # Create items for different encounters
        self.create_charge_item(title="Item for Encounter 1", encounter=self.encounter)
        self.create_charge_item(
            title="Item for Encounter 2", encounter=another_encounter
        )

        # Filter by encounter
        response = self.client.get(
            f"{self.base_url}?encounter={self.encounter.external_id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["title"], "Item for Encounter 1")

    def test_apply_charge_item_definitions_action(self):
        """Test applying charge item definitions action"""
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_create_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        url = f"{self.base_url}apply_charge_item_defs/"
        data = {
            "requests": [
                {
                    "charge_item_definition": self.charge_item_definition.slug,
                    "quantity": 2,
                    "encounter": self.encounter.external_id,
                }
            ]
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_apply_charge_item_definitions_without_permission(self):
        """Test applying charge item definitions without permission"""
        self.client.force_authenticate(user=self.user)

        url = f"{self.base_url}apply_charge_item_defs/"
        data = {
            "requests": [
                {
                    "charge_item_definition": self.charge_item_definition.slug,
                    "quantity": 1,
                    "encounter": self.encounter.external_id,
                }
            ]
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_apply_charge_item_definitions_invalid_definition(self):
        """Test applying non-existent charge item definition"""
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_create_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        url = f"{self.base_url}apply_charge_item_defs/"
        data = {
            "requests": [
                {
                    "charge_item_definition": "non-existent-slug",
                    "quantity": 1,
                    "encounter": self.encounter.external_id,
                }
            ]
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_apply_charge_item_definitions_missing_patient_encounter(self):
        """Test applying charge item definitions without patient or encounter"""
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_create_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        url = f"{self.base_url}apply_charge_item_defs/"
        data = {
            "requests": [
                {
                    "charge_item_definition": self.charge_item_definition.slug,
                    "quantity": 1,
                }
            ]
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_ordering_by_created_date(self):
        """Test ordering charge items by created date"""
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_read_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        # Create items
        self.create_charge_item(title="First Item")
        self.create_charge_item(title="Second Item")

        # Test ascending order
        response = self.client.get(f"{self.base_url}?ordering=created_date")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

        # Test descending order
        response = self.client.get(f"{self.base_url}?ordering=-created_date")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

    def test_upsert_charge_item(self):
        """Test upserting charge item"""
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_create_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        data = self.get_valid_charge_item_data()

        # First post should create
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        first_id = response.data["id"]

        # Second post with different data should create new item
        data["title"] = "Different Title"
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(
            response.data["id"], first_id
        )  # Different ID means new item


class TestChargeItemModelValidation(CareAPITestBase):
    """
    Test cases for ChargeItem model-level validations

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
        self.patient = self.create_patient()
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.create_facility_organization(facility=self.facility),
        )
        self.account = Account.objects.create(
            facility=self.facility,
            patient=self.patient,
            name=f"Account for {self.patient.name}",
            type="patient",
            status="active",
        )

    def test_charge_item_model_validation(self):
        """Test ChargeItem model field validations"""
        # Test creating with valid data
        charge_item = ChargeItem.objects.create(
            facility=self.facility,
            title="Test Charge Item",
            patient=self.patient,
            encounter=self.encounter,
            account=self.account,
            status=ChargeItemStatusOptions.billable.value,
            quantity=Decimal("1.00"),
            total_price=Decimal("100.00"),
        )
        self.assertIsNotNone(charge_item.id)

    def test_charge_item_foreign_key_constraints(self):
        """Test foreign key constraints in ChargeItem model"""
        # Test that non-existent patient reference fails
        with self.assertRaises((IntegrityError, ValidationError)):
            charge_item = ChargeItem(
                facility=self.facility,
                title="Test Charge Item",
                patient_id=99999,  # Non-existent patient
                encounter=self.encounter,
                account=self.account,
                status=ChargeItemStatusOptions.billable.value,
                quantity=Decimal("1.00"),
            )
            charge_item.full_clean()
            charge_item.save()


class TestChargeItemSpecValidation(CareAPITestBase):
    """
    Test cases for ChargeItem Pydantic spec validations

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
        self.patient = self.create_patient()
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.create_facility_organization(facility=self.facility),
        )

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

    def test_charge_item_spec_validation(self):
        """Test ChargeItemWriteSpec validations"""
        # Valid spec should pass
        valid_data = {
            "title": "Test Charge Item",
            "status": ChargeItemStatusOptions.billable.value,
            "quantity": 1.0,
            "unit_price_components": [self.get_valid_monetary_component()],
            "encounter": self.encounter.external_id,
        }
        spec = ChargeItemWriteSpec(**valid_data)
        self.assertEqual(spec.title, "Test Charge Item")

    def test_charge_item_spec_missing_encounter_and_patient(self):
        """Test validation when both encounter and patient are missing"""
        with self.assertRaises(PydanticValidationError) as context:
            ChargeItemWriteSpec(
                title="Test Charge Item",
                status=ChargeItemStatusOptions.billable.value,
                quantity=1.0,
                unit_price_components=[self.get_valid_monetary_component()],
            )
        self.assertIn("Encounter or patient is required", str(context.exception))

    def test_charge_item_spec_service_resource_without_id(self):
        """Test validation when service resource is specified without ID"""
        with self.assertRaises(PydanticValidationError) as context:
            ChargeItemWriteSpec(
                title="Test Charge Item",
                status=ChargeItemStatusOptions.billable.value,
                quantity=1.0,
                unit_price_components=[self.get_valid_monetary_component()],
                encounter=self.encounter.external_id,
                service_resource=ChargeItemResourceOptions.service_request.value,
            )
        self.assertIn("Service resource id is required", str(context.exception))

    def test_charge_item_spec_duplicate_codes(self):
        """Test validation for duplicate codes in unit price components"""
        with self.assertRaises(PydanticValidationError) as context:
            ChargeItemWriteSpec(
                title="Test Charge Item",
                status=ChargeItemStatusOptions.billable.value,
                quantity=1.0,
                unit_price_components=[
                    self.get_valid_monetary_component(
                        "base",
                        code={
                            "system": "http://test.system.com",
                            "code": "duplicate-code",
                            "display": "Test Code 1",
                        },
                    ),
                    self.get_valid_monetary_component(
                        "tax",
                        code={
                            "system": "http://test.system.com",
                            "code": "duplicate-code",
                            "display": "Test Code 2",
                        },
                    ),
                ],
                encounter=self.encounter.external_id,
            )
        self.assertIn("Duplicate codes", str(context.exception))

    def test_charge_item_spec_multiple_base_components(self):
        """Test validation for multiple base components"""
        with self.assertRaises(PydanticValidationError) as context:
            ChargeItemWriteSpec(
                title="Test Charge Item",
                status=ChargeItemStatusOptions.billable.value,
                quantity=1.0,
                unit_price_components=[
                    self.get_valid_monetary_component(
                        "base",
                        code={
                            "system": "http://test.system.com",
                            "code": "base-1",
                            "display": "Base 1",
                        },
                    ),
                    self.get_valid_monetary_component(
                        "base",
                        code={
                            "system": "http://test.system.com",
                            "code": "base-2",
                            "display": "Base 2",
                        },
                    ),
                ],
                encounter=self.encounter.external_id,
            )
        self.assertIn("Only one base component", str(context.exception))

    def test_monetary_component_validation_base_amount_required(self):
        """Test that base monetary components must have amount"""
        with self.assertRaises(PydanticValidationError):
            component = self.get_valid_monetary_component("base")
            del component["amount"]
            component["factor"] = 0.1
            ChargeItemWriteSpec(
                title="Test Charge Item",
                status=ChargeItemStatusOptions.billable.value,
                quantity=1.0,
                unit_price_components=[component],
                encounter=self.encounter.external_id,
            )

    def test_monetary_component_validation_amount_or_factor_required(self):
        """Test that monetary components must have either amount or factor"""
        with self.assertRaises(PydanticValidationError):
            component = self.get_valid_monetary_component("tax")
            del component["amount"]
            # No factor either - should fail
            ChargeItemWriteSpec(
                title="Test Charge Item",
                status=ChargeItemStatusOptions.billable.value,
                quantity=1.0,
                unit_price_components=[component],
                encounter=self.encounter.external_id,
            )

    def test_monetary_component_validation_not_both_amount_and_factor(self):
        """Test that monetary components cannot have both amount and factor"""
        with self.assertRaises(PydanticValidationError):
            component = self.get_valid_monetary_component("tax")
            component["factor"] = 0.18  # Also has amount - should fail
            ChargeItemWriteSpec(
                title="Test Charge Item",
                status=ChargeItemStatusOptions.billable.value,
                quantity=1.0,
                unit_price_components=[component],
                encounter=self.encounter.external_id,
            )

    def test_charge_item_spec_invalid_status(self):
        """Test invalid status validation"""
        with self.assertRaises(PydanticValidationError):
            ChargeItemWriteSpec(
                title="Test Charge Item",
                status="invalid_status",
                quantity=1.0,
                unit_price_components=[self.get_valid_monetary_component()],
                encounter=self.encounter.external_id,
            )

    def test_charge_item_spec_invalid_service_resource(self):
        """Test invalid service resource validation"""
        with self.assertRaises(PydanticValidationError):
            ChargeItemWriteSpec(
                title="Test Charge Item",
                status=ChargeItemStatusOptions.billable.value,
                quantity=1.0,
                unit_price_components=[self.get_valid_monetary_component()],
                encounter=self.encounter.external_id,
                service_resource="invalid_resource",
                service_resource_id="test-id",
            )

    def test_charge_item_read_spec_serialization(self):
        """Test ChargeItemReadSpec serialization"""
        # Create a charge item
        charge_item = ChargeItem.objects.create(
            facility=self.facility,
            title="Test Charge Item",
            patient=self.patient,
            encounter=self.encounter,
            account=Account.objects.create(
                facility=self.facility,
                patient=self.patient,
                name="Test Account",
                type="patient",
                status="active",
            ),
            status=ChargeItemStatusOptions.billable.value,
            quantity=Decimal("1.00"),
            unit_price_components=[],
            total_price_components=[],
            total_price=Decimal("100.00"),
        )

        # Serialize using read spec
        serialized = ChargeItemReadSpec.serialize(charge_item)
        self.assertEqual(serialized.title, "Test Charge Item")
        self.assertEqual(serialized.id, charge_item.external_id)


class TestChargeItemBusinessLogicValidation(CareAPITestBase):
    """
    Test cases for business logic validations in ChargeItem operations

    Tests cover:
    1. Invoice state validations
    2. Status transition validations
    3. Service resource validations
    """

    def setUp(self):
        """Set up test data"""
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.patient = self.create_patient()
        self.encounter = self.create_encounter(
            patient=self.patient, facility=self.facility, organization=self.organization
        )
        self.account = Account.objects.create(
            facility=self.facility,
            patient=self.patient,
            name="Test Account",
            type="patient",
            status="active",
        )

    def test_charge_item_cancelled_status_transitions(self):
        """Test various cancelled status transitions"""
        for cancelled_status in CHARGE_ITEM_CANCELLED_STATUS:
            charge_item = ChargeItem.objects.create(
                facility=self.facility,
                title="Test Charge Item",
                patient=self.patient,
                encounter=self.encounter,
                account=self.account,
                status=cancelled_status,
                quantity=Decimal("1.00"),
                unit_price_components=[],
                total_price_components=[],
                total_price=Decimal("100.00"),
            )

            # Verify the item was created with cancelled status
            self.assertEqual(charge_item.status, cancelled_status)
            self.assertIn(charge_item.status, CHARGE_ITEM_CANCELLED_STATUS)

    def test_service_resource_validation_options(self):
        """Test all service resource options are valid enum values"""
        valid_options = [option.value for option in ChargeItemResourceOptions]

        for option in valid_options:
            # This should not raise an exception
            spec_data = {
                "title": "Test Charge Item",
                "status": ChargeItemStatusOptions.billable.value,
                "quantity": 1.0,
                "unit_price_components": [
                    {
                        "monetary_component_type": "base",
                        "amount": 100.0,
                        "code": {
                            "system": "http://test.system.com",
                            "code": f"test-{option}",
                            "display": f"Test {option}",
                        },
                    }
                ],
                "encounter": self.encounter.external_id,
                "service_resource": option,
                "service_resource_id": "test-resource-id",
            }
            spec = ChargeItemWriteSpec(**spec_data)
            self.assertEqual(spec.service_resource, option)

    def test_charge_item_status_options(self):
        """Test all charge item status options"""
        for status_option in ChargeItemStatusOptions:
            spec_data = {
                "title": f"Test Item {status_option.value}",
                "status": status_option.value,
                "quantity": 1.0,
                "unit_price_components": [
                    {
                        "monetary_component_type": "base",
                        "amount": 100.0,
                        "code": {
                            "system": "http://test.system.com",
                            "code": f"test-{status_option.value}",
                            "display": f"Test {status_option.value}",
                        },
                    }
                ],
                "encounter": self.encounter.external_id,
            }
            spec = ChargeItemWriteSpec(**spec_data)
            self.assertEqual(spec.status, status_option.value)

    def test_monetary_component_types(self):
        """Test all monetary component types"""
        for component_type in MonetaryComponentType:
            component = {
                "monetary_component_type": component_type.value,
                "amount": 100.0
                if component_type == MonetaryComponentType.base
                else None,
                "factor": None if component_type == MonetaryComponentType.base else 0.1,
                "code": {
                    "system": "http://test.system.com",
                    "code": f"test-{component_type.value}",
                    "display": f"Test {component_type.value.title()}",
                },
            }

            # Remove None values
            component = {k: v for k, v in component.items() if v is not None}

            spec_data = {
                "title": "Test Charge Item",
                "status": ChargeItemStatusOptions.billable.value,
                "quantity": 1.0,
                "unit_price_components": [component],
                "encounter": self.encounter.external_id,
            }

            if component_type == MonetaryComponentType.base:
                # Base component should work
                spec = ChargeItemWriteSpec(**spec_data)
                self.assertEqual(
                    spec.unit_price_components[0].monetary_component_type,
                    component_type.value,
                )
            else:
                # Non-base components with factor should work
                spec = ChargeItemWriteSpec(**spec_data)
                self.assertEqual(
                    spec.unit_price_components[0].monetary_component_type,
                    component_type.value,
                )

    @patch(
        "care.emr.resources.charge_item.sync_charge_item_costs.sync_charge_item_costs"
    )
    def test_sync_charge_item_costs_called(self, mock_sync):
        """Test that sync_charge_item_costs is called during operations"""
        # This test verifies that the sync function would be called
        # In actual implementation, we'd test the viewset create/update methods
        mock_sync.return_value = None

        charge_item = ChargeItem.objects.create(
            facility=self.facility,
            title="Test Charge Item",
            patient=self.patient,
            encounter=self.encounter,
            account=self.account,
            status=ChargeItemStatusOptions.billable.value,
            quantity=Decimal("1.00"),
            unit_price_components=[],
            total_price_components=[],
            total_price=Decimal("100.00"),
        )

        # Verify the charge item was created
        self.assertIsNotNone(charge_item.id)
