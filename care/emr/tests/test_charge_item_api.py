from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.urls import reverse
from pydantic import ValidationError as PydanticValidationError
from rest_framework import status

from care.emr.api.viewsets.charge_item import (
    ApplyChargeItemDefinitionRequest,
    ApplyMultipleChargeItemDefinitionRequest,
    validate_service_resource,
)
from care.emr.models.account import Account
from care.emr.models.charge_item import ChargeItem
from care.emr.models.charge_item_definition import ChargeItemDefinition
from care.emr.resources.account.spec import (
    AccountBillingStatusOptions,
    AccountStatusOptions,
)
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
from care.emr.resources.encounter.constants import COMPLETED_CHOICES
from care.security.permissions.charge_item import ChargeItemPermissions
from care.utils.tests.base import CareAPITestBase


class TestChargeItemViewSet(CareAPITestBase):
    def setUp(self):
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
            name=f"Account for {self.patient.name}",
            status=AccountStatusOptions.active.value,
            billing_status=AccountBillingStatusOptions.open.value,
        )

        self.charge_item_definition = ChargeItemDefinition.objects.create(
            facility=self.facility,
            status=ChargeItemDefinitionStatusOptions.active.value,
            title="Test Charge Definition",
            slug=f"f-{self.facility.external_id}-test-charge-def",
            price_components=[
                {
                    "monetary_component_type": "base",
                    "currency": "INR",
                    "amount": "100.00",
                }
            ],
        )

        self.base_url = reverse(
            "charge_item-list",
            kwargs={"facility_external_id": self.facility.external_id},
        )

    def _get_detail_url(self, charge_item_id):
        return reverse(
            "charge_item-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": charge_item_id,
            },
        )

    def get_valid_charge_item_data(self, **kwargs):
        data = {
            "title": self.fake.sentence(nb_words=4),
            "description": self.fake.text(),
            "status": ChargeItemStatusOptions.billable.value,
            "quantity": 1.0,
            "unit_price_components": [
                {
                    "monetary_component_type": "base",
                    "currency": "INR",
                    "amount": "100.00",
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
                    "amount": "100.00",
                }
            ],
            "total_price_components": [
                {
                    "monetary_component_type": "base",
                    "currency": "INR",
                    "amount": "100.00",
                }
            ],
            "total_price": Decimal("100.00"),
        }
        data.update(**kwargs)
        return ChargeItem.objects.create(**data)

    def test_list_charge_items_without_permission(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_charge_items_with_permission(self):
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_read_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_charge_item_without_permission(self):
        self.client.force_authenticate(user=self.user)
        data = self.get_valid_charge_item_data()

        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_charge_item_with_permission(self):
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
                    "amount": "100.00",
                    "code": {
                        "system": "http://test.system.com",
                        "code": "duplicate-code",
                        "display": "Test Code 1",
                    },
                },
                {
                    "monetary_component_type": "tax",
                    "currency": "INR",
                    "amount": "18.00",
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
                    "amount": "100.00",
                    "code": {
                        "system": "http://test.system.com",
                        "code": "base-code-1",
                        "display": "Base Code 1",
                    },
                },
                {
                    "monetary_component_type": "base",
                    "currency": "INR",
                    "amount": "200.00",
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
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_create_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

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
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_create_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        data = self.get_valid_charge_item_data(status="invalid_status")
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_charge_item_missing_required_fields(self):
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_create_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        data = self.get_valid_charge_item_data()
        del data["title"]
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        data = self.get_valid_charge_item_data()
        del data["status"]
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        data = self.get_valid_charge_item_data()
        del data["quantity"]
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_charge_item_with_permission(self):
        role = self.create_role_with_permissions(
            [
                ChargeItemPermissions.can_update_charge_item.name,
                ChargeItemPermissions.can_read_charge_item.name,
            ]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

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
                    "amount": "200.00",
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
        role = self.create_role_with_permissions(
            [
                ChargeItemPermissions.can_update_charge_item.name,
                ChargeItemPermissions.can_read_charge_item.name,
            ]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

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
        self.client.force_authenticate(user=self.user)

        charge_item = self.create_charge_item()
        url = self._get_detail_url(charge_item.external_id)

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_by_status(self):
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_read_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        self.create_charge_item(
            status=ChargeItemStatusOptions.billable.value, title="Billable Item"
        )
        self.create_charge_item(
            status=ChargeItemStatusOptions.planned.value, title="Planned Item"
        )

        response = self.client.get(f"{self.base_url}?status=billable")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["title"], "Billable Item")

    def test_filter_by_title(self):
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_read_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        self.create_charge_item(title="Blood Test Charge")
        self.create_charge_item(title="X-Ray Charge")

        response = self.client.get(f"{self.base_url}?title=blood")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertTrue("Blood Test" in response.data["results"][0]["title"])

    def test_filter_by_account(self):
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_read_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        another_patient = self.create_patient()
        another_account = Account.objects.create(
            facility=self.facility,
            patient=another_patient,
            name=f"Account for {another_patient.name}",
            status=AccountStatusOptions.active.value,
            billing_status=AccountBillingStatusOptions.open.value,
        )

        self.create_charge_item(title="Item for Account 1", account=self.account)
        self.create_charge_item(
            title="Item for Account 2", account=another_account, patient=another_patient
        )

        response = self.client.get(
            f"{self.base_url}?account={self.account.external_id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["title"], "Item for Account 1")

    def test_filter_by_encounter(self):
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_read_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        another_encounter = self.create_encounter(
            patient=self.patient, facility=self.facility, organization=self.organization
        )

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
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_create_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        data = self.get_valid_charge_item_data()

        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        first_id = response.data["id"]

        data["title"] = "Different Title"
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.data["id"], first_id)


class TestChargeItemModelValidation(CareAPITestBase):
    def setUp(self):
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
            status=AccountStatusOptions.active.value,
            billing_status=AccountBillingStatusOptions.open.value,
        )

    def test_charge_item_model_validation(self):
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
        with self.assertRaises((IntegrityError, ValidationError)):
            charge_item = ChargeItem(
                facility=self.facility,
                title="Test Charge Item",
                patient_id=99999,
                encounter=self.encounter,
                account=self.account,
                status=ChargeItemStatusOptions.billable.value,
                quantity=Decimal("1.00"),
            )
            charge_item.full_clean()
            charge_item.save()


class TestChargeItemSpecValidation(CareAPITestBase):
    def setUp(self):
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
        with self.assertRaises(PydanticValidationError) as context:
            ChargeItemWriteSpec(
                title="Test Charge Item",
                status=ChargeItemStatusOptions.billable.value,
                quantity=1.0,
                unit_price_components=[self.get_valid_monetary_component()],
            )
        self.assertIn("Encounter or patient is required", str(context.exception))

    def test_charge_item_spec_service_resource_without_id(self):
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
        with self.assertRaises(PydanticValidationError):
            component = self.get_valid_monetary_component("tax")
            del component["amount"]
            ChargeItemWriteSpec(
                title="Test Charge Item",
                status=ChargeItemStatusOptions.billable.value,
                quantity=1.0,
                unit_price_components=[component],
                encounter=self.encounter.external_id,
            )

    def test_monetary_component_validation_not_both_amount_and_factor(self):
        with self.assertRaises(PydanticValidationError):
            component = self.get_valid_monetary_component("tax")
            component["factor"] = 0.18
            ChargeItemWriteSpec(
                title="Test Charge Item",
                status=ChargeItemStatusOptions.billable.value,
                quantity=1.0,
                unit_price_components=[component],
                encounter=self.encounter.external_id,
            )

    def test_charge_item_spec_invalid_status(self):
        with self.assertRaises(PydanticValidationError):
            ChargeItemWriteSpec(
                title="Test Charge Item",
                status="invalid_status",
                quantity=1.0,
                unit_price_components=[self.get_valid_monetary_component()],
                encounter=self.encounter.external_id,
            )

    def test_charge_item_spec_invalid_service_resource(self):
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
        charge_item = ChargeItem.objects.create(
            facility=self.facility,
            title="Test Charge Item",
            patient=self.patient,
            encounter=self.encounter,
            account=Account.objects.create(
                facility=self.facility,
                patient=self.patient,
                name="Test Account",
                status=AccountStatusOptions.active.value,
                billing_status=AccountBillingStatusOptions.open.value,
            ),
            status=ChargeItemStatusOptions.billable.value,
            quantity=Decimal("1.00"),
            unit_price_components=[],
            total_price_components=[],
            total_price=Decimal("100.00"),
        )

        serialized = ChargeItemReadSpec.serialize(charge_item)
        self.assertEqual(serialized.title, "Test Charge Item")
        self.assertEqual(serialized.id, charge_item.external_id)


class TestChargeItemBusinessLogicValidation(CareAPITestBase):
    def setUp(self):
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
            status=AccountStatusOptions.active.value,
            billing_status=AccountBillingStatusOptions.open.value,
        )

    def test_charge_item_cancelled_status_transitions(self):
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

            self.assertEqual(charge_item.status, cancelled_status)
            self.assertIn(charge_item.status, CHARGE_ITEM_CANCELLED_STATUS)

    def test_service_resource_validation_options(self):
        valid_options = [option.value for option in ChargeItemResourceOptions]

        for option in valid_options:
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

            component = {k: v for k, v in component.items() if v is not None}

            spec_data = {
                "title": "Test Charge Item",
                "status": ChargeItemStatusOptions.billable.value,
                "quantity": 1.0,
                "unit_price_components": [component],
                "encounter": self.encounter.external_id,
            }

            if component_type == MonetaryComponentType.base:
                spec = ChargeItemWriteSpec(**spec_data)
                self.assertEqual(
                    spec.unit_price_components[0].monetary_component_type,
                    component_type.value,
                )
            else:
                spec = ChargeItemWriteSpec(**spec_data)
                self.assertEqual(
                    spec.unit_price_components[0].monetary_component_type,
                    component_type.value,
                )

    @patch(
        "care.emr.resources.charge_item.sync_charge_item_costs.sync_charge_item_costs"
    )
    def test_sync_charge_item_costs_called(self, mock_sync):
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

        self.assertIsNotNone(charge_item.id)


class TestChargeItemMissingCoverage(CareAPITestBase):
    def setUp(self):
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
            name=f"Account for {self.patient.name}",
            status=AccountStatusOptions.active.value,
            billing_status=AccountBillingStatusOptions.open.value,
        )

        self.charge_item_definition = ChargeItemDefinition.objects.create(
            facility=self.facility,
            status=ChargeItemDefinitionStatusOptions.active.value,
            title="Test Charge Definition",
            slug=f"f-{self.facility.external_id}-test-charge-def",
            price_components=[
                {
                    "monetary_component_type": "base",
                    "currency": "INR",
                    "amount": "100.00",
                }
            ],
        )

        self.base_url = reverse(
            "charge_item-list",
            kwargs={"facility_external_id": self.facility.external_id},
        )

    def _get_detail_url(self, charge_item_id):
        return reverse(
            "charge_item-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": charge_item_id,
            },
        )

    def get_valid_charge_item_data(self, **kwargs):
        data = {
            "title": self.fake.sentence(nb_words=4),
            "description": self.fake.text(),
            "status": ChargeItemStatusOptions.billable.value,
            "quantity": 1.0,
            "unit_price_components": [
                {
                    "monetary_component_type": "base",
                    "currency": "INR",
                    "amount": "100.00",
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
                    "amount": "100.00",
                }
            ],
            "total_price_components": [
                {
                    "monetary_component_type": "base",
                    "currency": "INR",
                    "amount": "100.00",
                }
            ],
            "total_price": Decimal("100.00"),
        }
        data.update(**kwargs)
        return ChargeItem.objects.create(**data)

    def test_validate_service_resource_with_invalid_resource_type(self):
        result = validate_service_resource(
            self.facility,
            "invalid_resource_type",
            "resource-id",
            self.patient,
            self.encounter,
        )
        self.assertFalse(result)

    def test_validate_service_resource_service_request_without_encounter(self):
        service_request = self.create_service_request(
            patient=self.patient, facility=self.facility, encounter=self.encounter
        )

        result = validate_service_resource(
            self.facility,
            ChargeItemResourceOptions.service_request.value,
            str(service_request.external_id),
            self.patient,
            None,
        )
        self.assertTrue(result)

    def test_validate_service_resource_bed_association_without_encounter(self):
        result = validate_service_resource(
            self.facility,
            ChargeItemResourceOptions.bed_association.value,
            "bed-id",
            self.patient,
            None,
        )
        self.assertFalse(result)

    def test_validate_service_resource_bed_association_wrong_facility(self):
        other_user = self.create_user()
        other_facility = self.create_facility(user=other_user)
        other_encounter = self.create_encounter(
            patient=self.patient,
            facility=other_facility,
            organization=self.create_facility_organization(facility=other_facility),
        )

        result = validate_service_resource(
            self.facility,
            ChargeItemResourceOptions.bed_association.value,
            "bed-id",
            self.patient,
            other_encounter,
        )
        self.assertFalse(result)

    def test_validate_service_resource_bed_association_completed_encounter(self):
        completed_encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
            status=COMPLETED_CHOICES[0],
        )

        result = validate_service_resource(
            self.facility,
            ChargeItemResourceOptions.bed_association.value,
            "bed-id",
            self.patient,
            completed_encounter,
        )
        self.assertFalse(result)

    def test_validate_service_resource_exception_handling(self):
        with patch(
            "care.emr.models.service_request.ServiceRequest.objects.filter"
        ) as mock_filter:
            mock_filter.side_effect = Exception("Database error")

            result = validate_service_resource(
                self.facility,
                ChargeItemResourceOptions.service_request.value,
                "resource-id",
                self.patient,
                self.encounter,
            )
            self.assertFalse(result)

    def test_create_charge_item_with_invalid_service_resource(self):
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_create_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        data = self.get_valid_charge_item_data(
            service_resource=ChargeItemResourceOptions.service_request.value,
            service_resource_id="non-existent-id",
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid service resource", str(response.data))

    def test_create_charge_item_with_wrong_facility_encounter(self):
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_create_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        other_user = self.create_user()
        other_facility = self.create_facility(user=other_user)
        other_encounter = self.create_encounter(
            patient=self.patient,
            facility=other_facility,
            organization=self.create_facility_organization(facility=other_facility),
        )

        data = self.get_valid_charge_item_data(encounter=other_encounter.external_id)
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not associated with the facility", str(response.data))

    def test_create_charge_item_with_wrong_facility_account(self):
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_create_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        other_user = self.create_user()
        other_facility = self.create_facility(user=other_user)
        other_account = Account.objects.create(
            facility=other_facility,
            patient=self.patient,
            name="Other Account",
            status=AccountStatusOptions.active.value,
            billing_status=AccountBillingStatusOptions.open.value,
        )

        data = self.get_valid_charge_item_data(account=other_account.external_id)
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not associated with the facility", str(response.data))

    def test_get_queryset_without_read_permission(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_apply_charge_item_defs_with_patient_only(self):
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
                    "patient": self.patient.external_id,
                }
            ]
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_apply_charge_item_defs_with_wrong_facility_definition(self):
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_create_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        other_user = self.create_user()
        other_facility = self.create_facility(user=other_user)
        other_definition = ChargeItemDefinition.objects.create(
            facility=other_facility,
            status=ChargeItemDefinitionStatusOptions.active.value,
            title="Other Definition",
            slug=f"f-{other_facility.external_id}-other-def",
        )

        url = f"{self.base_url}apply_charge_item_defs/"
        data = {
            "requests": [
                {
                    "charge_item_definition": other_definition.slug,
                    "quantity": 1,
                    "encounter": self.encounter.external_id,
                }
            ]
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_apply_charge_item_defs_with_wrong_facility_encounter(self):
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_create_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        other_user = self.create_user()
        other_facility = self.create_facility(user=other_user)
        other_encounter = self.create_encounter(
            patient=self.patient,
            facility=other_facility,
            organization=self.create_facility_organization(facility=other_facility),
        )

        url = f"{self.base_url}apply_charge_item_defs/"
        data = {
            "requests": [
                {
                    "charge_item_definition": self.charge_item_definition.slug,
                    "quantity": 1,
                    "encounter": other_encounter.external_id,
                }
            ]
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_apply_charge_item_defs_with_invalid_service_resource(self):
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
                    "encounter": self.encounter.external_id,
                    "service_resource": ChargeItemResourceOptions.service_request.value,
                    "service_resource_id": "invalid-id",
                }
            ]
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid service resource", str(response.data))

    def test_apply_charge_item_defs_without_patient_or_encounter(self):
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

    def test_apply_charge_item_defs_with_service_resource_and_encounter_none(self):
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_create_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        service_request = self.create_service_request(
            patient=self.patient, facility=self.facility, encounter=self.encounter
        )

        url = f"{self.base_url}apply_charge_item_defs/"
        data = {
            "requests": [
                {
                    "charge_item_definition": self.charge_item_definition.slug,
                    "quantity": 1,
                    "patient": self.patient.external_id,
                    "service_resource": ChargeItemResourceOptions.service_request.value,
                    "service_resource_id": str(service_request.external_id),
                }
            ]
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_facility_obj_with_invalid_facility_id(self):
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_read_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        invalid_url = reverse(
            "charge_item-list",
            kwargs={"facility_external_id": "invalid-facility-id"},
        )
        response = self.client.get(invalid_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_filter_by_service_resource(self):
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_read_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        service_request = self.create_service_request(
            patient=self.patient, facility=self.facility, encounter=self.encounter
        )

        self.create_charge_item(
            title="Service Request Item",
            service_resource=ChargeItemResourceOptions.service_request.value,
            service_resource_id=str(service_request.external_id),
        )
        self.create_charge_item(title="Regular Item")

        response = self.client.get(f"{self.base_url}?service_resource=service_request")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["title"], "Service Request Item")

    def test_filter_by_service_resource_id(self):
        role = self.create_role_with_permissions(
            [ChargeItemPermissions.can_read_charge_item.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        service_request = self.create_service_request(
            patient=self.patient, facility=self.facility, encounter=self.encounter
        )

        self.create_charge_item(
            title="Specific Service Request Item",
            service_resource=ChargeItemResourceOptions.service_request.value,
            service_resource_id=str(service_request.external_id),
        )
        self.create_charge_item(
            title="Other Service Request Item",
            service_resource=ChargeItemResourceOptions.service_request.value,
            service_resource_id="other-id",
        )

        response = self.client.get(
            f"{self.base_url}?service_resource_id={service_request.external_id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["title"], "Specific Service Request Item"
        )


class TestChargeItemPydanticValidation(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.patient = self.create_patient()
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.create_facility_organization(facility=self.facility),
        )

    def test_apply_charge_item_definition_request_missing_encounter_and_patient(self):
        with self.assertRaises(PydanticValidationError) as context:
            ApplyChargeItemDefinitionRequest(
                charge_item_definition="test-definition",
                quantity=1,
            )
        self.assertIn("Encounter or patient is required", str(context.exception))

    def test_apply_charge_item_definition_request_with_encounter_only(self):
        request = ApplyChargeItemDefinitionRequest(
            charge_item_definition="test-definition",
            quantity=1,
            encounter=self.encounter.external_id,
        )
        self.assertEqual(request.encounter, self.encounter.external_id)
        self.assertIsNone(request.patient)

    def test_apply_charge_item_definition_request_with_patient_only(self):
        request = ApplyChargeItemDefinitionRequest(
            charge_item_definition="test-definition",
            quantity=1,
            patient=self.patient.external_id,
        )
        self.assertEqual(request.patient, self.patient.external_id)
        self.assertIsNone(request.encounter)

    def test_apply_charge_item_definition_request_with_both_encounter_and_patient(self):
        request = ApplyChargeItemDefinitionRequest(
            charge_item_definition="test-definition",
            quantity=1,
            encounter=self.encounter.external_id,
            patient=self.patient.external_id,
        )
        self.assertEqual(request.encounter, self.encounter.external_id)
        self.assertEqual(request.patient, self.patient.external_id)

    def test_apply_charge_item_definition_request_service_resource_without_id(self):
        with self.assertRaises(PydanticValidationError) as context:
            ApplyChargeItemDefinitionRequest(
                charge_item_definition="test-definition",
                quantity=1,
                encounter=self.encounter.external_id,
                service_resource=ChargeItemResourceOptions.service_request.value,
            )
        self.assertIn("Service resource id is required", str(context.exception))

    def test_apply_charge_item_definition_request_service_resource_with_id(self):
        request = ApplyChargeItemDefinitionRequest(
            charge_item_definition="test-definition",
            quantity=1,
            encounter=self.encounter.external_id,
            service_resource=ChargeItemResourceOptions.service_request.value,
            service_resource_id="test-resource-id",
        )
        self.assertEqual(
            request.service_resource, ChargeItemResourceOptions.service_request.value
        )
        self.assertEqual(request.service_resource_id, "test-resource-id")

    def test_apply_charge_item_definition_request_without_service_resource(self):
        request = ApplyChargeItemDefinitionRequest(
            charge_item_definition="test-definition",
            quantity=1,
            encounter=self.encounter.external_id,
        )
        self.assertIsNone(request.service_resource)
        self.assertIsNone(request.service_resource_id)

    def test_apply_charge_item_definition_request_with_service_resource_id_but_no_resource(
        self,
    ):
        request = ApplyChargeItemDefinitionRequest(
            charge_item_definition="test-definition",
            quantity=1,
            encounter=self.encounter.external_id,
            service_resource_id="test-resource-id",
        )
        self.assertIsNone(request.service_resource)
        self.assertEqual(request.service_resource_id, "test-resource-id")

    def test_apply_multiple_charge_item_definition_request_empty_list(self):
        request = ApplyMultipleChargeItemDefinitionRequest(requests=[])
        self.assertEqual(len(request.requests), 0)

    def test_apply_multiple_charge_item_definition_request_single_item(self):
        single_request = ApplyChargeItemDefinitionRequest(
            charge_item_definition="test-definition",
            quantity=1,
            encounter=self.encounter.external_id,
        )

        multiple_request = ApplyMultipleChargeItemDefinitionRequest(
            requests=[single_request]
        )
        self.assertEqual(len(multiple_request.requests), 1)
        self.assertEqual(
            multiple_request.requests[0].charge_item_definition, "test-definition"
        )

    def test_apply_multiple_charge_item_definition_request_multiple_items(self):
        request1 = ApplyChargeItemDefinitionRequest(
            charge_item_definition="test-definition-1",
            quantity=1,
            encounter=self.encounter.external_id,
        )

        request2 = ApplyChargeItemDefinitionRequest(
            charge_item_definition="test-definition-2",
            quantity=2,
            patient=self.patient.external_id,
        )

        multiple_request = ApplyMultipleChargeItemDefinitionRequest(
            requests=[request1, request2]
        )
        self.assertEqual(len(multiple_request.requests), 2)
        self.assertEqual(
            multiple_request.requests[0].charge_item_definition, "test-definition-1"
        )
        self.assertEqual(
            multiple_request.requests[1].charge_item_definition, "test-definition-2"
        )
        self.assertEqual(multiple_request.requests[1].quantity, 2)

    def test_apply_charge_item_definition_request_all_service_resource_options(self):
        for option in ChargeItemResourceOptions:
            request = ApplyChargeItemDefinitionRequest(
                charge_item_definition="test-definition",
                quantity=1,
                encounter=self.encounter.external_id,
                service_resource=option.value,
                service_resource_id="test-resource-id",
            )
            self.assertEqual(request.service_resource, option.value)

    def test_apply_charge_item_definition_request_zero_quantity(self):
        request = ApplyChargeItemDefinitionRequest(
            charge_item_definition="test-definition",
            quantity=0,
            encounter=self.encounter.external_id,
        )
        self.assertEqual(request.quantity, 0)

    def test_apply_charge_item_definition_request_negative_quantity(self):
        request = ApplyChargeItemDefinitionRequest(
            charge_item_definition="test-definition",
            quantity=-1,
            encounter=self.encounter.external_id,
        )
        self.assertEqual(request.quantity, -1)

    def test_apply_charge_item_definition_request_large_quantity(self):
        request = ApplyChargeItemDefinitionRequest(
            charge_item_definition="test-definition",
            quantity=999999,
            encounter=self.encounter.external_id,
        )
        self.assertEqual(request.quantity, 999999)

    def test_apply_charge_item_definition_request_uuid_validation(self):
        import uuid

        valid_uuid = uuid.uuid4()

        request = ApplyChargeItemDefinitionRequest(
            charge_item_definition="test-definition",
            quantity=1,
            encounter=valid_uuid,
            patient=valid_uuid,
        )
        self.assertEqual(request.encounter, valid_uuid)
        self.assertEqual(request.patient, valid_uuid)

    def test_apply_charge_item_definition_request_string_charge_item_definition(self):
        test_strings = [
            "simple-slug",
            "complex-slug-with-dashes",
            "slug_with_underscores",
            "slug123with456numbers",
            "f-12345678-1234-1234-1234-123456789012-test-slug",
        ]

        for test_string in test_strings:
            request = ApplyChargeItemDefinitionRequest(
                charge_item_definition=test_string,
                quantity=1,
                encounter=self.encounter.external_id,
            )
            self.assertEqual(request.charge_item_definition, test_string)

    def test_model_validator_execution_order(self):
        with self.assertRaises(PydanticValidationError) as context:
            ApplyChargeItemDefinitionRequest(
                charge_item_definition="test-definition",
                quantity=1,
                service_resource=ChargeItemResourceOptions.service_request.value,
                service_resource_id="test-id",
            )

        self.assertIn("Encounter or patient is required", str(context.exception))

    def test_model_validator_service_resource_validation_after_encounter_patient(self):
        with self.assertRaises(PydanticValidationError) as context:
            ApplyChargeItemDefinitionRequest(
                charge_item_definition="test-definition",
                quantity=1,
                encounter=self.encounter.external_id,
                service_resource=ChargeItemResourceOptions.service_request.value,
            )

        self.assertIn("Service resource id is required", str(context.exception))

    def test_apply_charge_item_definition_request_defaults(self):
        request = ApplyChargeItemDefinitionRequest(
            charge_item_definition="test-definition",
            quantity=1,
            encounter=self.encounter.external_id,
        )

        self.assertIsNone(request.patient)
        self.assertIsNone(request.service_resource)
        self.assertIsNone(request.service_resource_id)
