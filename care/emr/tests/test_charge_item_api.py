import uuid
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import override_settings
from django.urls import reverse
from model_bakery import baker
from pydantic import ValidationError as PydanticValidationError
from rest_framework import status

from care.emr.api.viewsets.charge_item import (
    ApplyChargeItemDefinitionRequest,
    ApplyMultipleChargeItemDefinitionRequest,
    validate_service_resource,
)
from care.emr.locks.billing import AccountLock
from care.emr.models.account import Account
from care.emr.models.charge_item import ChargeItem
from care.emr.models.charge_item_definition import ChargeItemDefinition
from care.emr.models.invoice import Invoice
from care.emr.models.location import FacilityLocation, FacilityLocationEncounter
from care.emr.models.medication_dispense import MedicationDispense
from care.emr.models.scheduling.booking import TokenBooking
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
from care.emr.resources.charge_item.sync_charge_item_costs import (
    sync_charge_item_costs,
)
from care.emr.resources.charge_item_definition.spec import (
    ChargeItemDefinitionStatusOptions,
)
from care.emr.resources.common.monetary_component import MonetaryComponentType
from care.emr.resources.encounter.constants import COMPLETED_CHOICES
from care.emr.resources.invoice.spec import InvoiceStatusOptions
from care.security.permissions.charge_item import ChargeItemPermissions
from care.utils.tests.base import CareAPITestBase
from care.utils.time_util import care_now

# 22 integer digits, exceeds max_digits=20
OVERFLOW_VALUE = "10000000000000000000000.00"
# 14 integer digits + 6 decimal places = 20 total
MAX_VALID_VALUE = "99999999999999.999999"

READ_PERMISSIONS = (ChargeItemPermissions.can_read_charge_item,)
CREATE_PERMISSIONS = (ChargeItemPermissions.can_create_charge_item,)
UPDATE_PERMISSIONS = (
    ChargeItemPermissions.can_update_charge_item,
    ChargeItemPermissions.can_read_charge_item,
)


def make_coding(code, display=None):
    return {
        "system": "http://test.system.com",
        "code": code,
        "display": display or code,
    }


def make_price_component(component_type="base", amount="100.00", **kwargs):
    """Build a monetary component dict; keys passed as ``None`` are omitted."""
    component = {"monetary_component_type": component_type, "amount": amount, **kwargs}
    return {key: value for key, value in component.items() if value is not None}


class TestChargeItemViewSet(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.patient = self.create_patient()
        self.encounter = self.create_facility_encounter()
        self.account = self.create_account()
        self.charge_item_definition = self.create_charge_item_definition()
        self.base_url = reverse(
            "charge_item-list",
            kwargs={"facility_external_id": self.facility.external_id},
        )
        self.apply_defs_url = f"{self.base_url}apply_charge_item_defs/"
        self.change_account_url = reverse(
            "charge_item-change-account",
            kwargs={"facility_external_id": self.facility.external_id},
        )

    def authenticate_with(self, *permissions):
        """Authenticate as ``self.user``, granting ``permissions`` in the facility."""
        if permissions:
            role = self.create_role_with_permissions(
                [permission.name for permission in permissions]
            )
            self.attach_role_facility_organization_user(
                self.organization, self.user, role
            )
        self.client.force_authenticate(user=self.user)

    def get_detail_url(self, charge_item_id):
        return reverse(
            "charge_item-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": charge_item_id,
            },
        )

    def create_other_facility(self):
        return self.create_facility(user=self.create_user())

    def create_facility_encounter(self, patient=None, **kwargs):
        return self.create_encounter(
            patient=patient or self.patient,
            facility=self.facility,
            organization=self.organization,
            **kwargs,
        )

    def create_other_facility_encounter(self):
        other_facility = self.create_other_facility()
        return self.create_encounter(
            patient=self.patient,
            facility=other_facility,
            organization=self.create_facility_organization(facility=other_facility),
        )

    def create_account(self, **kwargs):
        patient = kwargs.pop("patient", self.patient)
        data = {
            "facility": self.facility,
            "patient": patient,
            "name": f"Account for {patient.name}",
            "status": AccountStatusOptions.active.value,
            "billing_status": AccountBillingStatusOptions.open.value,
        }
        data.update(**kwargs)
        return Account.objects.create(**data)

    def create_charge_item_definition(self, **kwargs):
        facility = kwargs.pop("facility", self.facility)
        data = {
            "facility": facility,
            "status": ChargeItemDefinitionStatusOptions.active.value,
            "title": "Test Charge Definition",
            "slug": f"f-{facility.external_id}-test-charge-def",
            "price_components": [make_price_component()],
        }
        data.update(**kwargs)
        return ChargeItemDefinition.objects.create(**data)

    def build_charge_item(self, **kwargs):
        data = {
            "facility": self.facility,
            "title": self.fake.sentence(nb_words=4),
            "patient": self.patient,
            "encounter": self.encounter,
            "account": self.account,
            "status": ChargeItemStatusOptions.billable.value,
            "quantity": Decimal("1.00"),
            "unit_price_components": [make_price_component()],
        }
        data.update(**kwargs)
        return ChargeItem(**data)

    def create_charge_item(self, **kwargs):
        data = {
            "total_price_components": [make_price_component()],
            "total_price": Decimal("100.00"),
        }
        data.update(**kwargs)
        charge_item = self.build_charge_item(**data)
        charge_item.save()
        return charge_item

    def create_invoice(
        self, charge_items, invoice_status, account=None, mark_billed=True
    ):
        invoice = Invoice.objects.create(
            facility=self.facility,
            patient=self.patient,
            account=account or self.account,
            status=invoice_status,
            charge_items=[item.id for item in charge_items],
        )
        update_fields = ["paid_invoice"]
        if mark_billed:
            update_fields.append("status")
        for item in charge_items:
            item.paid_invoice = invoice
            if mark_billed:
                item.status = ChargeItemStatusOptions.billed.value
            item.save(update_fields=update_fields)
        return invoice

    def create_bed_association(self, encounter):
        location = baker.make(
            FacilityLocation,
            facility=self.facility,
            status="active",
            operational_status="O",
            name="Test Bed",
            mode="instance",
            form="bd",
        )
        return baker.make(
            FacilityLocationEncounter,
            location=location,
            encounter=encounter,
            status="active",
            start_datetime=care_now(),
        )

    def create_service_resources(self):
        bed_association = self.create_bed_association(self.encounter)
        location = bed_association.location
        product_knowledge = baker.make("emr.ProductKnowledge", facility=self.facility)
        product = baker.make(
            "emr.Product", facility=self.facility, product_knowledge=product_knowledge
        )
        inventory_item = baker.make(
            "emr.InventoryItem", location=location, product=product
        )
        schedulable_resource = baker.make(
            "emr.SchedulableResource", facility=self.facility, user=self.user
        )
        token_slot = baker.make("emr.TokenSlot", resource=schedulable_resource)
        return {
            ChargeItemResourceOptions.service_request: self.create_service_request(
                patient=self.patient, facility=self.facility, encounter=self.encounter
            ),
            ChargeItemResourceOptions.bed_association: bed_association,
            ChargeItemResourceOptions.medication_dispense: baker.make(
                MedicationDispense,
                patient=self.patient,
                encounter=self.encounter,
                location=location,
                item=inventory_item,
            ),
            ChargeItemResourceOptions.appointment: baker.make(
                TokenBooking, patient=self.patient, token_slot=token_slot
            ),
        }

    def get_valid_charge_item_data(self, **kwargs):
        data = {
            "title": self.fake.sentence(nb_words=4),
            "description": self.fake.text(),
            "status": ChargeItemStatusOptions.billable.value,
            "quantity": 1.0,
            "unit_price_components": [
                make_price_component(code=make_coding("test-code-001", "Test Code"))
            ],
            "encounter": self.encounter.external_id,
            "account": self.account.external_id,
        }
        data.update(**kwargs)
        return data

    def get_update_data(self, **kwargs):
        data = {
            "title": "Updated Title",
            "status": ChargeItemStatusOptions.billable.value,
            "quantity": 1.0,
            "unit_price_components": [make_price_component()],
        }
        data.update(**kwargs)
        return data

    def update_charge_item(self, charge_item, **kwargs):
        return self.client.put(
            self.get_detail_url(charge_item.external_id),
            self.get_update_data(**kwargs),
            format="json",
        )

    def get_write_spec_data(self, **kwargs):
        data = {
            "title": "Test Charge Item",
            "status": ChargeItemStatusOptions.billable.value,
            "quantity": 1.0,
            "unit_price_components": [
                make_price_component(code=make_coding("test-base"))
            ],
            "encounter": self.encounter.external_id,
        }
        data.update(**kwargs)
        return data

    def get_apply_definition_request(self, **kwargs):
        """Build an apply request payload; keys passed as ``None`` are omitted."""
        data = {
            "charge_item_definition": self.charge_item_definition.slug,
            "quantity": 1,
            "encounter": self.encounter.external_id,
        }
        data.update(**kwargs)
        return {key: value for key, value in data.items() if value is not None}

    def apply_charge_item_definitions(self, **kwargs):
        return self.client.post(
            self.apply_defs_url,
            {"requests": [self.get_apply_definition_request(**kwargs)]},
            format="json",
        )

    def build_apply_definition_request(self, **kwargs):
        data = {
            "charge_item_definition": "test-definition",
            "quantity": 1,
            "encounter": self.encounter.external_id,
        }
        data.update(**kwargs)
        return ApplyChargeItemDefinitionRequest(**data)

    def setup_change_account(self):
        self.source_account = self.create_account(name="Source Account")
        self.target_account = self.create_account(name="Target Account")
        self.charge_item = self.create_charge_item(
            title="Consultation", encounter=None, account=self.source_account
        )
        self.authenticate_with(*CREATE_PERMISSIONS)

    def change_account(self, target_account=None):
        target_account = target_account or self.target_account
        return self.client.post(
            self.change_account_url,
            {
                "charge_items": [str(self.charge_item.external_id)],
                "target_account": str(target_account.external_id),
            },
            format="json",
        )

    def racing_account_lock(self, on_acquire):
        """Run `on_acquire` right after the account rows are locked."""

        class RacingAccountLock(AccountLock):
            def __enter__(self):
                result = super().__enter__()
                on_acquire()
                return result

        return patch("care.emr.api.viewsets.charge_item.AccountLock", RacingAccountLock)

    def assert_item_not_moved(self):
        self.charge_item.refresh_from_db()
        self.assertEqual(self.charge_item.account_id, self.source_account.id)

    def assert_synced_total(self, unit_price_components, expected_total):
        charge_item = self.build_charge_item(
            unit_price_components=unit_price_components
        )
        sync_charge_item_costs(charge_item)
        self.assertEqual(charge_item.total_price, Decimal(expected_total))

    # Listing charge items: GET charge_item-list.

    def test_list_charge_items_without_permission(self):
        """Listing charge items without read permission is forbidden."""
        self.authenticate_with()
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_charge_items_with_permission(self):
        """Listing charge items succeeds with read permission."""
        self.authenticate_with(*READ_PERMISSIONS)

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_facility_obj_with_invalid_facility_id(self):
        """Requests to an unknown facility return 404."""
        self.authenticate_with(*READ_PERMISSIONS)

        invalid_url = reverse(
            "charge_item-list",
            kwargs={"facility_external_id": "invalid-facility-id"},
        )
        response = self.client.get(invalid_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_filter_by_status(self):
        """The status filter returns only items with the given status."""
        self.authenticate_with(*READ_PERMISSIONS)

        self.create_charge_item(
            status=ChargeItemStatusOptions.billable.value, title="Billable Item"
        )
        self.create_charge_item(
            status=ChargeItemStatusOptions.billed.value, title="Billed Item"
        )

        response = self.client.get(f"{self.base_url}?status=billable")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["title"], "Billable Item")

    def test_filter_by_title(self):
        """The title filter performs a case-insensitive partial match."""
        self.authenticate_with(*READ_PERMISSIONS)

        self.create_charge_item(title="Blood Test Charge")
        self.create_charge_item(title="X-Ray Charge")

        response = self.client.get(f"{self.base_url}?title=blood")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertIn("Blood Test", response.data["results"][0]["title"])

    def test_filter_by_account(self):
        """The account filter returns only items of the given account."""
        self.authenticate_with(*READ_PERMISSIONS)

        another_patient = self.create_patient()
        another_account = self.create_account(patient=another_patient)

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
        """The encounter filter returns only items of the given encounter."""
        self.authenticate_with(*READ_PERMISSIONS)

        another_encounter = self.create_facility_encounter()

        self.create_charge_item(title="Item for Encounter 1", encounter=self.encounter)
        self.create_charge_item(
            title="Item for Encounter 2", encounter=another_encounter
        )

        response = self.client.get(
            f"{self.base_url}?encounter={self.encounter.external_id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["title"], "Item for Encounter 1")

    def test_filter_by_service_resource(self):
        """The service resource filter returns only items of that resource type."""
        self.authenticate_with(*READ_PERMISSIONS)
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
        """The service resource id filter returns only items of that resource."""
        self.authenticate_with(*READ_PERMISSIONS)
        service_request = self.create_service_request(
            patient=self.patient, facility=self.facility, encounter=self.encounter
        )
        other_service_request = self.create_service_request(
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
            service_resource_id=str(other_service_request.external_id),
        )

        response = self.client.get(
            f"{self.base_url}?service_resource_id={service_request.external_id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["title"], "Specific Service Request Item"
        )

    # Retrieving a charge item: GET charge_item-detail.

    def test_retrieve_charge_item_with_permission(self):
        """Retrieving a charge item succeeds with read permission."""
        self.authenticate_with(*READ_PERMISSIONS)
        charge_item = self.create_charge_item(title="Test Charge Item")

        response = self.client.get(self.get_detail_url(charge_item.external_id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Test Charge Item")

    def test_retrieve_charge_item_without_permission(self):
        """Retrieving a charge item without read permission is forbidden."""
        self.authenticate_with()
        charge_item = self.create_charge_item()

        response = self.client.get(self.get_detail_url(charge_item.external_id))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # Creating a charge item: POST charge_item-list.

    def test_create_charge_item_without_permission(self):
        """Creating a charge item without create permission is forbidden."""
        self.authenticate_with()

        response = self.client.post(
            self.base_url, self.get_valid_charge_item_data(), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_charge_item_with_permission(self):
        """Creating a charge item with create permission returns the created item."""
        self.authenticate_with(*CREATE_PERMISSIONS)

        data = self.get_valid_charge_item_data()
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], data["title"])

    def test_create_charge_item_with_patient_only(self):
        """A charge item can be created against a patient without an encounter."""
        self.authenticate_with(*CREATE_PERMISSIONS)

        data = self.get_valid_charge_item_data(patient=self.patient.external_id)
        del data["encounter"]

        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_charge_item_missing_patient_and_encounter(self):
        """Creating a charge item without a patient or encounter is rejected."""
        self.authenticate_with(*CREATE_PERMISSIONS)

        data = self.get_valid_charge_item_data()
        del data["encounter"]

        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_charge_item_missing_required_fields(self):
        """Omitting title, status or quantity is rejected."""
        self.authenticate_with(*CREATE_PERMISSIONS)

        for field in ("title", "status", "quantity"):
            with self.subTest(field=field):
                data = self.get_valid_charge_item_data()
                del data[field]
                response = self.client.post(self.base_url, data, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_charge_item_invalid_status(self):
        """An unknown charge item status is rejected."""
        self.authenticate_with(*CREATE_PERMISSIONS)

        data = self.get_valid_charge_item_data(status="invalid_status")
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_charge_item_duplicate_price_component_codes(self):
        """Price components sharing the same code are rejected."""
        self.authenticate_with(*CREATE_PERMISSIONS)

        data = self.get_valid_charge_item_data(
            unit_price_components=[
                make_price_component(code=make_coding("duplicate-code")),
                make_price_component(
                    "tax", amount="18.00", code=make_coding("duplicate-code")
                ),
            ]
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_charge_item_multiple_base_components(self):
        """More than one base price component is rejected."""
        self.authenticate_with(*CREATE_PERMISSIONS)

        data = self.get_valid_charge_item_data(
            unit_price_components=[
                make_price_component(code=make_coding("base-code-1")),
                make_price_component(amount="200.00", code=make_coding("base-code-2")),
            ]
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_charge_item_with_service_resource(self):
        """A charge item can be linked to a valid service request."""
        self.authenticate_with(*CREATE_PERMISSIONS)

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
        """A service resource without a service resource id is rejected."""
        self.authenticate_with(*CREATE_PERMISSIONS)

        data = self.get_valid_charge_item_data(
            service_resource=ChargeItemResourceOptions.service_request.value
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_charge_item_with_invalid_service_resource(self):
        """Creating with a non-existent service resource is rejected."""
        self.authenticate_with(*CREATE_PERMISSIONS)

        data = self.get_valid_charge_item_data(
            service_resource=ChargeItemResourceOptions.service_request.value,
            service_resource_id=str(uuid.uuid4()),
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid service resource", str(response.data))

    def test_create_charge_item_with_wrong_facility_encounter(self):
        """Creating with an encounter of another facility is rejected."""
        self.authenticate_with(*CREATE_PERMISSIONS)
        other_encounter = self.create_other_facility_encounter()

        data = self.get_valid_charge_item_data(encounter=other_encounter.external_id)
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not associated with the facility", str(response.data))

    def test_create_charge_item_with_wrong_facility_account(self):
        """Creating with an account of another facility is rejected."""
        self.authenticate_with(*CREATE_PERMISSIONS)
        other_account = self.create_account(
            facility=self.create_other_facility(), name="Other Account"
        )

        data = self.get_valid_charge_item_data(account=other_account.external_id)
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not associated with the facility", str(response.data))

    def test_create_charge_item_with_performer_actor(self):
        """Creating with a facility user as performer stores the performer."""
        self.authenticate_with(*CREATE_PERMISSIONS)

        data = self.get_valid_charge_item_data(performer_actor=self.user.external_id)
        response = self.client.post(self.base_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        charge_item = ChargeItem.objects.get(external_id=response.data["id"])
        self.assertEqual(charge_item.performer_actor_id, self.user.id)

    def test_create_charge_item_with_performer_not_in_facility(self):
        """Creating with a performer outside the facility is rejected."""
        self.authenticate_with(*CREATE_PERMISSIONS)
        outsider = self.create_user()

        data = self.get_valid_charge_item_data(performer_actor=outsider.external_id)
        response = self.client.post(self.base_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Performer is not associated with the facility", str(response.data)
        )
        self.assertFalse(ChargeItem.objects.filter(performer_actor=outsider).exists())

    def test_create_charge_item_without_account_uses_default_account(self):
        """Creating without an account attaches the patient's default open account."""
        self.authenticate_with(*CREATE_PERMISSIONS)
        patient = self.create_patient()
        encounter = self.create_facility_encounter(patient=patient)

        data = self.get_valid_charge_item_data(encounter=encounter.external_id)
        del data["account"]
        response = self.client.post(self.base_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        charge_item = ChargeItem.objects.get(external_id=response.data["id"])
        default_account = Account.objects.get(patient=patient, facility=self.facility)
        self.assertEqual(charge_item.account_id, default_account.id)
        self.assertEqual(default_account.status, AccountStatusOptions.active.value)
        self.assertEqual(
            default_account.billing_status, AccountBillingStatusOptions.open.value
        )

    def test_create_charge_item_overflow_quantity_returns_400(self):
        """Test that API returns 400 (not 500) for overflowing quantity values."""
        self.authenticate_with(*CREATE_PERMISSIONS)

        data = self.get_valid_charge_item_data(quantity=OVERFLOW_VALUE)
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_charge_item_overflow_amount_returns_400(self):
        """Test that API returns 400 (not 500) for overflowing amount values."""
        self.authenticate_with(*CREATE_PERMISSIONS)

        data = self.get_valid_charge_item_data(
            unit_price_components=[
                make_price_component(
                    amount=OVERFLOW_VALUE, code=make_coding("test-code-001")
                )
            ]
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Bulk upserting charge items: POST charge_item-upsert.

    def test_upsert_charge_item(self):
        """Posting the same payload twice creates two distinct charge items."""
        self.authenticate_with(*CREATE_PERMISSIONS)

        data = {"datapoints": [self.get_valid_charge_item_data()]}
        upsert_url = f"{self.base_url}upsert/"

        response = self.client.post(upsert_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        first_id = response.data[0]["id"]

        response = self.client.post(upsert_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        second_id = response.data[0]["id"]
        self.assertNotEqual(second_id, first_id)
        self.assertEqual(
            ChargeItem.objects.filter(external_id__in=[first_id, second_id]).count(), 2
        )

    def test_upsert_charge_item_overflow_quantity_returns_400(self):
        """Test that upsert API returns 400 (not 500) for overflowing quantity values."""
        self.authenticate_with(*CREATE_PERMISSIONS)

        data = {
            "datapoints": [
                self.get_valid_charge_item_data(
                    quantity=OVERFLOW_VALUE,
                    unit_price_components=[make_price_component(amount="10.00")],
                )
            ]
        }
        response = self.client.post(f"{self.base_url}upsert/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Updating and cancelling a charge item: PUT charge_item-detail.

    def test_update_charge_item_with_permission(self):
        """Updating a charge item succeeds with update permission."""
        self.authenticate_with(*UPDATE_PERMISSIONS)
        charge_item = self.create_charge_item()

        response = self.update_charge_item(
            charge_item,
            description="Updated description",
            quantity=2.0,
            unit_price_components=[
                make_price_component(
                    amount="200.00", code=make_coding("updated-code", "Updated Code")
                )
            ],
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Updated Title")

    def test_update_charge_item_without_permission(self):
        """Updating a charge item with only read permission is forbidden."""
        self.authenticate_with(*READ_PERMISSIONS)
        charge_item = self.create_charge_item()

        response = self.update_charge_item(charge_item, quantity=2.0)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_cancelled_charge_item(self):
        """A cancelled charge item cannot be updated."""
        self.authenticate_with(*UPDATE_PERMISSIONS)
        charge_item = self.create_charge_item(
            status=ChargeItemStatusOptions.entered_in_error.value
        )

        response = self.update_charge_item(
            charge_item,
            status=ChargeItemStatusOptions.entered_in_error.value,
            quantity=2.0,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cancelled", str(response.data))

    def test_update_charge_item_cannot_set_billed_status(self):
        """Billed and paid statuses cannot be set through an update."""
        self.authenticate_with(*UPDATE_PERMISSIONS)
        charge_item = self.create_charge_item()

        for item_status in [
            ChargeItemStatusOptions.billed.value,
            ChargeItemStatusOptions.paid.value,
        ]:
            response = self.update_charge_item(charge_item, status=item_status)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("can only be set by an invoice", str(response.data))

    def test_update_charge_item_conflicts_when_account_changes_during_update(self):
        """An update is rejected with 423 if the item moves to another account mid-update."""
        self.authenticate_with(*UPDATE_PERMISSIONS)
        charge_item = self.create_charge_item(title="Original Title")
        other_account = self.create_account(name="Other Account")
        original_refresh = ChargeItem.refresh_from_db

        def refresh_after_concurrent_move(instance, *args, **kwargs):
            ChargeItem.objects.filter(id=instance.id).update(account=other_account)
            return original_refresh(instance, *args, **kwargs)

        with patch.object(
            ChargeItem,
            "refresh_from_db",
            autospec=True,
            side_effect=refresh_after_concurrent_move,
        ):
            response = self.update_charge_item(charge_item)

        self.assertEqual(response.status_code, status.HTTP_423_LOCKED)
        charge_item.refresh_from_db()
        self.assertEqual(charge_item.title, "Original Title")

    def test_update_charge_item_in_issued_or_balanced_invoice(self):
        """Items in issued or balanced invoices cannot be updated."""
        self.authenticate_with(*UPDATE_PERMISSIONS)
        for invoice_status in [
            InvoiceStatusOptions.issued.value,
            InvoiceStatusOptions.balanced.value,
        ]:
            charge_item = self.create_charge_item(title="Original Title")
            self.create_invoice([charge_item], invoice_status)

            response = self.update_charge_item(
                charge_item, status=ChargeItemStatusOptions.billed.value
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("already balanced or issued", str(response.data))
            charge_item.refresh_from_db()
            self.assertEqual(charge_item.title, "Original Title")

    def test_update_status_of_charge_item_in_draft_invoice(self):
        """The status of an item in a draft invoice cannot be changed."""
        self.authenticate_with(*UPDATE_PERMISSIONS)
        charge_item = self.create_charge_item()
        self.create_invoice([charge_item], InvoiceStatusOptions.draft.value)

        response = self.update_charge_item(
            charge_item, status=ChargeItemStatusOptions.billable.value
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Remove charge item from its invoice", str(response.data))
        charge_item.refresh_from_db()
        self.assertEqual(charge_item.status, ChargeItemStatusOptions.billed.value)

    def test_update_charge_item_in_draft_invoice_syncs_invoice(self):
        """Updating an item in a draft invoice recalculates the invoice totals."""
        self.authenticate_with(*UPDATE_PERMISSIONS)
        charge_item = self.create_charge_item()
        invoice = self.create_invoice([charge_item], InvoiceStatusOptions.draft.value)

        response = self.update_charge_item(
            charge_item, status=ChargeItemStatusOptions.billed.value, quantity=3.0
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invoice.refresh_from_db()
        self.assertEqual(invoice.total_net, Decimal("300.00"))
        self.assertEqual(invoice.total_gross, Decimal("300.00"))

    def test_update_charge_item_with_non_editable_definition_keeps_prices(self):
        """Items from a non-editable definition keep their quantity and prices on update."""
        self.authenticate_with(*UPDATE_PERMISSIONS)
        self.charge_item_definition.can_edit_charge_item = False
        self.charge_item_definition.save(update_fields=["can_edit_charge_item"])
        charge_item = self.create_charge_item(
            charge_item_definition=self.charge_item_definition
        )

        response = self.update_charge_item(
            charge_item,
            quantity=5.0,
            unit_price_components=[make_price_component(amount="500.00")],
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        charge_item.refresh_from_db()
        self.assertEqual(charge_item.title, "Updated Title")
        self.assertEqual(charge_item.quantity, Decimal("1.00"))
        self.assertEqual(charge_item.total_price, Decimal("100.00"))
        self.assertEqual(charge_item.unit_price_components[0]["amount"], "100.00")

    def test_cancel_charge_item_without_cancel_permission(self):
        """Cancelling after the free cancel period requires cancel permission."""
        self.authenticate_with(*UPDATE_PERMISSIONS)
        charge_item = self.create_charge_item()

        with override_settings(CHARGE_ITEM_FREE_CANCEL_PERIOD_MINUTES=0):
            response = self.update_charge_item(
                charge_item, status=ChargeItemStatusOptions.entered_in_error.value
            )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        charge_item.refresh_from_db()
        self.assertEqual(charge_item.status, ChargeItemStatusOptions.billable.value)

    def test_cancel_charge_item_with_cancel_permission(self):
        """Cancelling after the free cancel period succeeds with cancel permission."""
        self.authenticate_with(
            *UPDATE_PERMISSIONS, ChargeItemPermissions.can_cancel_charge_item
        )
        charge_item = self.create_charge_item()

        with override_settings(CHARGE_ITEM_FREE_CANCEL_PERIOD_MINUTES=0):
            response = self.update_charge_item(
                charge_item, status=ChargeItemStatusOptions.entered_in_error.value
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        charge_item.refresh_from_db()
        self.assertEqual(
            charge_item.status, ChargeItemStatusOptions.entered_in_error.value
        )

    def test_cancel_charge_item_within_free_cancel_period(self):
        """Cancelling within the free cancel period needs no cancel permission."""
        self.authenticate_with(*UPDATE_PERMISSIONS)
        charge_item = self.create_charge_item()

        with override_settings(CHARGE_ITEM_FREE_CANCEL_PERIOD_MINUTES=60):
            response = self.update_charge_item(
                charge_item, status=ChargeItemStatusOptions.entered_in_error.value
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        charge_item.refresh_from_db()
        self.assertEqual(
            charge_item.status, ChargeItemStatusOptions.entered_in_error.value
        )

    # Applying charge item definitions: POST charge_item-apply-charge-item-defs.

    def test_apply_charge_item_definitions_without_permission(self):
        """Applying charge item definitions without create permission is forbidden."""
        self.authenticate_with()

        response = self.apply_charge_item_definitions()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_apply_charge_item_definitions_action(self):
        """Applying a charge item definition to an encounter succeeds."""
        self.authenticate_with(*CREATE_PERMISSIONS)

        response = self.apply_charge_item_definitions(quantity=2)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_apply_charge_item_defs_with_patient_only(self):
        """A charge item definition can be applied to a patient without an encounter."""
        self.authenticate_with(*CREATE_PERMISSIONS)

        response = self.apply_charge_item_definitions(
            quantity=2, encounter=None, patient=self.patient.external_id
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_apply_charge_item_definitions_missing_patient_encounter(self):
        """Applying a definition without a patient or encounter is rejected."""
        self.authenticate_with(*CREATE_PERMISSIONS)

        response = self.apply_charge_item_definitions(encounter=None)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Encounter or patient is required", str(response.data))
        self.assertFalse(ChargeItem.objects.exists())

    def test_apply_charge_item_definitions_invalid_definition(self):
        """Applying an unknown charge item definition returns 404."""
        self.authenticate_with(*CREATE_PERMISSIONS)

        response = self.apply_charge_item_definitions(
            charge_item_definition="non-existent-slug"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_apply_charge_item_defs_with_wrong_facility_definition(self):
        """Applying a definition from another facility returns 404."""
        self.authenticate_with(*CREATE_PERMISSIONS)
        other_facility = self.create_other_facility()
        other_definition = self.create_charge_item_definition(
            facility=other_facility,
            title="Other Definition",
            slug=f"f-{other_facility.external_id}-other-def",
        )

        response = self.apply_charge_item_definitions(
            charge_item_definition=other_definition.slug
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn(
            "No ChargeItemDefinition matches the given query", str(response.data)
        )
        self.assertFalse(
            ChargeItem.objects.filter(charge_item_definition=other_definition).exists()
        )

    def test_apply_charge_item_defs_with_wrong_facility_encounter(self):
        """Applying a definition to an encounter of another facility returns 404."""
        self.authenticate_with(*CREATE_PERMISSIONS)
        other_encounter = self.create_other_facility_encounter()

        response = self.apply_charge_item_definitions(
            encounter=other_encounter.external_id
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_apply_charge_item_defs_with_invalid_service_resource(self):
        """Applying a definition with a non-existent service resource is rejected."""
        self.authenticate_with(*CREATE_PERMISSIONS)

        response = self.apply_charge_item_definitions(
            service_resource=ChargeItemResourceOptions.service_request.value,
            service_resource_id=str(uuid.uuid4()),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid service resource", str(response.data))

    def test_apply_charge_item_defs_with_service_resource_and_encounter_none(self):
        """A definition can be applied with a service resource and no encounter."""
        self.authenticate_with(*CREATE_PERMISSIONS)
        service_request = self.create_service_request(
            patient=self.patient, facility=self.facility, encounter=self.encounter
        )

        response = self.apply_charge_item_definitions(
            encounter=None,
            patient=self.patient.external_id,
            service_resource=ChargeItemResourceOptions.service_request.value,
            service_resource_id=str(service_request.external_id),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_apply_charge_item_defs_with_account(self):
        """Applying a definition with an account attaches the item to that account."""
        self.authenticate_with(*CREATE_PERMISSIONS)
        target_account = self.create_account(name="Selected Account")

        response = self.apply_charge_item_definitions(
            account=target_account.external_id
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        charge_item = ChargeItem.objects.get(
            charge_item_definition=self.charge_item_definition
        )
        self.assertEqual(charge_item.account_id, target_account.id)

    def test_apply_charge_item_defs_with_inactive_account(self):
        """Applying a definition with an inactive account returns 404."""
        self.authenticate_with(*CREATE_PERMISSIONS)
        inactive_account = self.create_account(
            status=AccountStatusOptions.inactive.value
        )

        response = self.apply_charge_item_definitions(
            account=inactive_account.external_id
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(
            ChargeItem.objects.filter(
                charge_item_definition=self.charge_item_definition
            ).exists()
        )

    def test_apply_charge_item_defs_with_performer_actor(self):
        """Applying a definition with a facility user as performer stores the performer."""
        self.authenticate_with(*CREATE_PERMISSIONS)

        response = self.apply_charge_item_definitions(
            performer_actor=self.user.external_id
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        charge_item = ChargeItem.objects.get(
            charge_item_definition=self.charge_item_definition
        )
        self.assertEqual(charge_item.performer_actor_id, self.user.id)

    def test_apply_charge_item_defs_with_performer_not_in_facility(self):
        """Applying a definition with a performer outside the facility is rejected."""
        self.authenticate_with(*CREATE_PERMISSIONS)
        outsider = self.create_user()

        response = self.apply_charge_item_definitions(
            performer_actor=outsider.external_id
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Performer is not associated with the facility", str(response.data)
        )
        self.assertFalse(
            ChargeItem.objects.filter(
                charge_item_definition=self.charge_item_definition
            ).exists()
        )

    # Moving charge items between accounts: POST charge_item-change-account.

    def test_change_account_without_permission(self):
        """Changing account without permission is forbidden."""
        self.setup_change_account()
        self.client.force_authenticate(user=self.create_user())

        response = self.change_account()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assert_item_not_moved()

    def test_change_account_moves_item_and_rebalances_accounts(self):
        """Moving an item updates both account balances and the updater."""
        self.setup_change_account()
        self.source_account.total_billable_charge_items = Decimal("100.00")
        self.source_account.save(update_fields=["total_billable_charge_items"])
        self.source_account.refresh_from_db()
        self.target_account.refresh_from_db()
        self.assertEqual(
            self.source_account.total_billable_charge_items, Decimal("100.00")
        )
        self.assertEqual(self.target_account.total_billable_charge_items, 0)

        response = self.change_account()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.charge_item.refresh_from_db()
        self.assertEqual(self.charge_item.account_id, self.target_account.id)
        self.assertEqual(self.charge_item.updated_by_id, self.user.id)
        self.source_account.refresh_from_db()
        self.target_account.refresh_from_db()
        self.assertEqual(self.source_account.total_billable_charge_items, 0)
        self.assertEqual(
            self.target_account.total_billable_charge_items, Decimal("100.00")
        )

    def test_change_account_to_closed_completed_account(self):
        """Items cannot be moved to a closed and completed account."""
        self.setup_change_account()
        self.target_account.billing_status = (
            AccountBillingStatusOptions.closed_completed.value
        )
        self.target_account.save(update_fields=["billing_status"])

        response = self.change_account()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Cannot transfer charge item to a closed and completed account",
            str(response.data),
        )
        self.assert_item_not_moved()

    def test_change_account_from_closed_completed_account(self):
        """Items cannot be moved out of a closed and completed account."""
        self.setup_change_account()
        self.source_account.billing_status = (
            AccountBillingStatusOptions.closed_completed.value
        )
        self.source_account.save(update_fields=["billing_status"])

        response = self.change_account()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Cannot transfer charge items from closed and completed accounts",
            str(response.data),
        )
        self.assert_item_not_moved()

    def test_change_account_to_account_in_another_facility(self):
        """Items cannot be moved to an account of another facility."""
        self.setup_change_account()
        other_account = self.create_account(facility=self.create_other_facility())

        response = self.change_account(other_account)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assert_item_not_moved()

    def test_change_account_to_another_patients_account(self):
        """Items cannot be moved to another patient's account."""
        self.setup_change_account()
        other_account = self.create_account(patient=self.create_patient())

        response = self.change_account(other_account)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assert_item_not_moved()

    def test_change_account_with_non_billable_item(self):
        """Only billable items can be moved between accounts."""
        self.setup_change_account()
        self.charge_item.status = ChargeItemStatusOptions.not_billable.value
        self.charge_item.save(update_fields=["status"])

        response = self.change_account()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("should be billable", str(response.data))
        self.assert_item_not_moved()

    def test_change_account_with_item_attached_to_invoice(self):
        """Items attached to an invoice cannot be moved between accounts."""
        self.setup_change_account()
        self.create_invoice(
            [self.charge_item],
            InvoiceStatusOptions.draft.value,
            account=self.source_account,
            mark_billed=False,
        )

        response = self.change_account()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already belongs to another invoice", str(response.data))
        self.assert_item_not_moved()

    def test_change_account_when_source_account_closes_concurrently(self):
        """The move is rejected if the source account closes after locking."""
        self.setup_change_account()

        def close_source_account():
            Account.objects.filter(id=self.source_account.id).update(
                billing_status=AccountBillingStatusOptions.closed_completed.value
            )

        with self.racing_account_lock(close_source_account):
            response = self.change_account()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Cannot transfer charge items from closed and completed accounts",
            str(response.data),
        )
        self.assert_item_not_moved()

    def test_change_account_when_target_account_closes_concurrently(self):
        """The move is rejected if the target account closes after locking."""
        self.setup_change_account()

        def close_target_account():
            Account.objects.filter(id=self.target_account.id).update(
                billing_status=AccountBillingStatusOptions.closed_completed.value
            )

        with self.racing_account_lock(close_target_account):
            response = self.change_account()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Cannot transfer charge items from closed and completed accounts",
            str(response.data),
        )
        self.assert_item_not_moved()

    def test_change_account_when_item_moves_concurrently(self):
        """The move is rejected with 423 if the item moves to another account after locking."""
        self.setup_change_account()
        other_account = self.create_account(name="Other Account")

        def move_item():
            ChargeItem.objects.filter(id=self.charge_item.id).update(
                account=other_account
            )

        with self.racing_account_lock(move_item):
            response = self.change_account()

        self.assertEqual(response.status_code, status.HTTP_423_LOCKED)
        # The simulated move shares the locked transaction, so it is rolled back too.
        self.assert_item_not_moved()

    def test_change_account_when_item_is_removed_concurrently(self):
        """The move returns 404 if the item leaves the patient after locking."""
        self.setup_change_account()

        def remove_item():
            ChargeItem.objects.filter(id=self.charge_item.id).update(
                patient=self.create_patient()
            )

        with self.racing_account_lock(remove_item):
            response = self.change_account()

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assert_item_not_moved()

    # The validate_service_resource helper used by create and apply.

    def test_validate_service_resource_with_invalid_resource_type(self):
        """An unknown service resource type is invalid."""
        service_request = self.create_service_request(
            patient=self.patient, facility=self.facility, encounter=self.encounter
        )
        result = validate_service_resource(
            self.facility,
            "invalid_resource_type",
            str(service_request.external_id),
            self.patient,
            self.encounter,
        )
        self.assertFalse(result)

    def test_validate_service_resource_service_request_without_encounter(self):
        """A service request of the patient is valid without an encounter."""
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
        """A bed association requires an encounter."""
        bed_association = self.create_bed_association(self.encounter)
        result = validate_service_resource(
            self.facility,
            ChargeItemResourceOptions.bed_association.value,
            str(bed_association.external_id),
            self.patient,
            None,
        )
        self.assertFalse(result)

    def test_validate_service_resource_bed_association_wrong_facility(self):
        """A bed association is invalid for an encounter of another facility."""
        bed_association = self.create_bed_association(self.encounter)

        result = validate_service_resource(
            self.create_other_facility(),
            ChargeItemResourceOptions.bed_association.value,
            str(bed_association.external_id),
            self.patient,
            self.encounter,
        )
        self.assertFalse(result)

    def test_validate_service_resource_bed_association_completed_encounter(self):
        """A bed association is invalid for a completed encounter."""
        completed_encounter = self.create_facility_encounter(
            status=COMPLETED_CHOICES[0]
        )
        bed_association = self.create_bed_association(completed_encounter)

        result = validate_service_resource(
            self.facility,
            ChargeItemResourceOptions.bed_association.value,
            str(bed_association.external_id),
            self.patient,
            completed_encounter,
        )
        self.assertFalse(result)

    def test_validate_service_resource_bed_association_active_encounter(self):
        """A bed association is valid only for the encounter it belongs to."""
        bed_association = self.create_bed_association(self.encounter)

        self.assertTrue(
            validate_service_resource(
                self.facility,
                ChargeItemResourceOptions.bed_association.value,
                str(bed_association.external_id),
                self.patient,
                self.encounter,
            )
        )
        self.assertFalse(
            validate_service_resource(
                self.facility,
                ChargeItemResourceOptions.bed_association.value,
                str(bed_association.external_id),
                self.patient,
                self.create_facility_encounter(),
            )
        )

    def test_validate_service_resource_exception_handling(self):
        """Errors during service resource lookup are treated as invalid."""
        service_request = self.create_service_request(
            patient=self.patient, facility=self.facility, encounter=self.encounter
        )
        with patch(
            "care.emr.models.service_request.ServiceRequest.objects.filter"
        ) as mock_filter:
            mock_filter.side_effect = Exception("Database error")

            result = validate_service_resource(
                self.facility,
                ChargeItemResourceOptions.service_request.value,
                str(service_request.external_id),
                self.patient,
                self.encounter,
            )
            self.assertFalse(result)

    # Request specs of the apply_charge_item_defs endpoint.

    def test_apply_charge_item_definition_request_defaults(self):
        """Optional apply request fields default to None."""
        request = self.build_apply_definition_request()

        self.assertIsNone(request.patient)
        self.assertIsNone(request.service_resource)
        self.assertIsNone(request.service_resource_id)

    def test_apply_charge_item_definition_request_missing_encounter_and_patient(self):
        """The apply request requires an encounter or a patient."""
        with self.assertRaises(PydanticValidationError) as context:
            self.build_apply_definition_request(encounter=None)
        self.assertIn("Encounter or patient is required", str(context.exception))

    def test_apply_charge_item_definition_request_with_encounter_only(self):
        """The apply request accepts an encounter without a patient."""
        request = self.build_apply_definition_request()
        self.assertEqual(request.encounter, self.encounter.external_id)
        self.assertIsNone(request.patient)

    def test_apply_charge_item_definition_request_with_patient_only(self):
        """The apply request accepts a patient without an encounter."""
        request = self.build_apply_definition_request(
            encounter=None, patient=self.patient.external_id
        )
        self.assertEqual(request.patient, self.patient.external_id)
        self.assertIsNone(request.encounter)

    def test_apply_charge_item_definition_request_with_both_encounter_and_patient(self):
        """The apply request accepts both an encounter and a patient."""
        request = self.build_apply_definition_request(patient=self.patient.external_id)
        self.assertEqual(request.encounter, self.encounter.external_id)
        self.assertEqual(request.patient, self.patient.external_id)

    def test_apply_charge_item_definition_request_service_resource_without_id(self):
        """The apply request requires an id when a service resource is set."""
        with self.assertRaises(PydanticValidationError) as context:
            self.build_apply_definition_request(
                service_resource=ChargeItemResourceOptions.service_request.value
            )
        self.assertIn("Service resource id is required", str(context.exception))

    def test_apply_charge_item_definition_request_service_resource_with_id(self):
        """The apply request keeps the service resource and its id."""
        service_request = self.create_service_request(
            patient=self.patient, facility=self.facility, encounter=self.encounter
        )
        request = self.build_apply_definition_request(
            service_resource=ChargeItemResourceOptions.service_request.value,
            service_resource_id=str(service_request.external_id),
        )
        self.assertEqual(
            request.service_resource, ChargeItemResourceOptions.service_request.value
        )
        self.assertEqual(request.service_resource_id, str(service_request.external_id))

    def test_apply_charge_item_definition_request_with_service_resource_id_but_no_resource(
        self,
    ):
        """The apply request accepts a service resource id without a resource type."""
        service_request = self.create_service_request(
            patient=self.patient, facility=self.facility, encounter=self.encounter
        )
        request = self.build_apply_definition_request(
            service_resource_id=str(service_request.external_id)
        )
        self.assertIsNone(request.service_resource)
        self.assertEqual(request.service_resource_id, str(service_request.external_id))

    def test_apply_charge_item_definition_request_all_service_resource_options(self):
        """The apply request accepts every service resource option."""
        for option, resource in self.create_service_resources().items():
            with self.subTest(option=option):
                request = self.build_apply_definition_request(
                    service_resource=option.value,
                    service_resource_id=str(resource.external_id),
                )
                self.assertEqual(request.service_resource, option.value)
                self.assertEqual(request.service_resource_id, str(resource.external_id))

    def test_model_validator_execution_order(self):
        """The encounter/patient check runs before the service resource check."""
        service_request = self.create_service_request(
            patient=self.patient, facility=self.facility, encounter=self.encounter
        )
        with self.assertRaises(PydanticValidationError) as context:
            self.build_apply_definition_request(
                encounter=None,
                service_resource=ChargeItemResourceOptions.service_request.value,
                service_resource_id=str(service_request.external_id),
            )

        self.assertIn("Encounter or patient is required", str(context.exception))

    def test_apply_charge_item_definition_request_quantities(self):
        """The apply request accepts zero, negative and large quantities."""
        for quantity in (0, -1, 999999):
            with self.subTest(quantity=quantity):
                request = self.build_apply_definition_request(quantity=quantity)
                self.assertEqual(request.quantity, quantity)

    def test_apply_charge_item_definition_request_uuid_validation(self):
        """The apply request accepts UUIDs for encounter and patient."""
        valid_uuid = uuid.uuid4()

        request = self.build_apply_definition_request(
            encounter=valid_uuid, patient=valid_uuid
        )
        self.assertEqual(request.encounter, valid_uuid)
        self.assertEqual(request.patient, valid_uuid)

    def test_apply_charge_item_definition_request_string_charge_item_definition(self):
        """The apply request accepts any slug format as the definition."""
        test_strings = [
            "simple-slug",
            "complex-slug-with-dashes",
            "slug_with_underscores",
            "slug123with456numbers",
            "f-12345678-1234-1234-1234-123456789012-test-slug",
        ]

        for test_string in test_strings:
            request = self.build_apply_definition_request(
                charge_item_definition=test_string
            )
            self.assertEqual(request.charge_item_definition, test_string)

    def test_apply_multiple_charge_item_definition_request_empty_list(self):
        """The bulk apply request accepts an empty list."""
        request = ApplyMultipleChargeItemDefinitionRequest(requests=[])
        self.assertEqual(len(request.requests), 0)

    def test_apply_multiple_charge_item_definition_request_single_item(self):
        """The bulk apply request accepts a single request."""
        multiple_request = ApplyMultipleChargeItemDefinitionRequest(
            requests=[self.build_apply_definition_request()]
        )
        self.assertEqual(len(multiple_request.requests), 1)
        self.assertEqual(
            multiple_request.requests[0].charge_item_definition, "test-definition"
        )

    def test_apply_multiple_charge_item_definition_request_multiple_items(self):
        """The bulk apply request keeps multiple requests in order."""
        request1 = self.build_apply_definition_request(
            charge_item_definition="test-definition-1"
        )
        request2 = self.build_apply_definition_request(
            charge_item_definition="test-definition-2",
            quantity=2,
            encounter=None,
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

    # ChargeItemWriteSpec and monetary component validation.

    def test_charge_item_spec_validation(self):
        """The write spec accepts a valid payload."""
        spec = ChargeItemWriteSpec(**self.get_write_spec_data())
        self.assertEqual(spec.title, "Test Charge Item")

    def test_charge_item_spec_missing_encounter_and_patient(self):
        """The write spec requires an encounter or a patient."""
        with self.assertRaises(PydanticValidationError) as context:
            ChargeItemWriteSpec(**self.get_write_spec_data(encounter=None))
        self.assertIn("Encounter or patient is required", str(context.exception))

    def test_charge_item_spec_invalid_status(self):
        """The write spec rejects an unknown status."""
        with self.assertRaises(PydanticValidationError):
            ChargeItemWriteSpec(**self.get_write_spec_data(status="invalid_status"))

    def test_charge_item_status_options(self):
        """The write spec accepts every status except billed and paid."""
        for status_option in ChargeItemStatusOptions:
            spec_data = self.get_write_spec_data(
                title=f"Test Item {status_option.value}", status=status_option.value
            )
            if status_option in (
                ChargeItemStatusOptions.billed,
                ChargeItemStatusOptions.paid,
            ):
                with self.assertRaises(PydanticValidationError):
                    ChargeItemWriteSpec(**spec_data)
                continue
            spec = ChargeItemWriteSpec(**spec_data)
            self.assertEqual(spec.status, status_option.value)

    def test_charge_item_spec_service_resource_without_id(self):
        """The write spec requires an id when a service resource is set."""
        with self.assertRaises(PydanticValidationError) as context:
            ChargeItemWriteSpec(
                **self.get_write_spec_data(
                    service_resource=ChargeItemResourceOptions.service_request.value
                )
            )
        self.assertIn("Service resource id is required", str(context.exception))

    def test_charge_item_spec_invalid_service_resource(self):
        """The write spec rejects an unknown service resource type."""
        service_request = self.create_service_request(
            patient=self.patient, facility=self.facility, encounter=self.encounter
        )
        with self.assertRaises(PydanticValidationError):
            ChargeItemWriteSpec(
                **self.get_write_spec_data(
                    service_resource="invalid_resource",
                    service_resource_id=str(service_request.external_id),
                )
            )

    def test_service_resource_validation_options(self):
        """The write spec accepts every service resource option."""
        for option, resource in self.create_service_resources().items():
            with self.subTest(option=option):
                spec = ChargeItemWriteSpec(
                    **self.get_write_spec_data(
                        service_resource=option.value,
                        service_resource_id=str(resource.external_id),
                    )
                )
                self.assertEqual(spec.service_resource, option.value)
                self.assertEqual(spec.service_resource_id, str(resource.external_id))

    def test_charge_item_spec_duplicate_codes(self):
        """The write spec rejects price components with duplicate codes."""
        with self.assertRaises(PydanticValidationError) as context:
            ChargeItemWriteSpec(
                **self.get_write_spec_data(
                    unit_price_components=[
                        make_price_component(code=make_coding("duplicate-code")),
                        make_price_component("tax", code=make_coding("duplicate-code")),
                    ]
                )
            )
        self.assertIn("Duplicate codes", str(context.exception))

    def test_charge_item_spec_multiple_base_components(self):
        """The write spec allows only one base price component."""
        with self.assertRaises(PydanticValidationError) as context:
            ChargeItemWriteSpec(
                **self.get_write_spec_data(
                    unit_price_components=[
                        make_price_component(code=make_coding("base-1")),
                        make_price_component(code=make_coding("base-2")),
                    ]
                )
            )
        self.assertIn("Only one base component", str(context.exception))

    def test_monetary_component_types(self):
        """The write spec accepts every monetary component type."""
        for component_type in MonetaryComponentType:
            is_base = component_type == MonetaryComponentType.base
            component = make_price_component(
                component_type.value,
                amount=100.0 if is_base else None,
                factor=None if is_base else 0.1,
                code=make_coding(f"test-{component_type.value}"),
            )

            spec = ChargeItemWriteSpec(
                **self.get_write_spec_data(unit_price_components=[component])
            )
            self.assertEqual(
                spec.unit_price_components[0].monetary_component_type,
                component_type.value,
            )

    def test_monetary_component_validation_base_amount_required(self):
        """A base price component must have an amount, not a factor."""
        with self.assertRaises(PydanticValidationError):
            ChargeItemWriteSpec(
                **self.get_write_spec_data(
                    unit_price_components=[
                        make_price_component(
                            amount=None, factor=0.1, code=make_coding("test-base")
                        )
                    ]
                )
            )

    def test_monetary_component_validation_amount_or_factor_required(self):
        """A non-base price component needs either an amount or a factor."""
        with self.assertRaises(PydanticValidationError):
            ChargeItemWriteSpec(
                **self.get_write_spec_data(
                    unit_price_components=[
                        make_price_component(
                            "tax", amount=None, code=make_coding("test-tax")
                        )
                    ]
                )
            )

    def test_monetary_component_validation_not_both_amount_and_factor(self):
        """A price component cannot have both an amount and a factor."""
        with self.assertRaises(PydanticValidationError):
            ChargeItemWriteSpec(
                **self.get_write_spec_data(
                    unit_price_components=[
                        make_price_component(
                            "tax", factor=0.18, code=make_coding("test-tax")
                        )
                    ]
                )
            )

    def test_charge_item_spec_overflow_quantity(self):
        """Test that overflowing quantity values are rejected with validation error."""
        with self.assertRaises(PydanticValidationError) as context:
            ChargeItemWriteSpec(
                **self.get_write_spec_data(quantity=Decimal(OVERFLOW_VALUE))
            )
        self.assertIn("decimal", str(context.exception).lower())

    def test_charge_item_spec_valid_max_quantity(self):
        """Test that maximum valid quantity (14 integer digits + 6 decimal places) is accepted."""
        spec = ChargeItemWriteSpec(
            **self.get_write_spec_data(quantity=Decimal(MAX_VALID_VALUE))
        )
        self.assertEqual(spec.quantity, Decimal(MAX_VALID_VALUE))

    def test_monetary_component_overflow_amount(self):
        """Test that overflowing amount values in monetary component are rejected."""
        with self.assertRaises(PydanticValidationError) as context:
            ChargeItemWriteSpec(
                **self.get_write_spec_data(
                    quantity=Decimal("1.00"),
                    unit_price_components=[
                        make_price_component(
                            amount=Decimal(OVERFLOW_VALUE),
                            code=make_coding("test-base"),
                        )
                    ],
                )
            )
        self.assertIn("decimal", str(context.exception).lower())

    def test_monetary_component_overflow_factor(self):
        """Test that overflowing factor values in monetary component are rejected."""
        with self.assertRaises(PydanticValidationError) as context:
            ChargeItemWriteSpec(
                **self.get_write_spec_data(
                    quantity=Decimal("1.00"),
                    unit_price_components=[
                        make_price_component(
                            amount=Decimal("100.00"), code=make_coding("test-base")
                        ),
                        make_price_component(
                            "tax",
                            amount=None,
                            factor=Decimal(OVERFLOW_VALUE),
                            code=make_coding("test-tax"),
                        ),
                    ],
                )
            )
        self.assertIn("decimal", str(context.exception).lower())

    def test_monetary_component_valid_max_amount(self):
        """Test that maximum valid amount is accepted."""
        spec = ChargeItemWriteSpec(
            **self.get_write_spec_data(
                quantity=Decimal("1.00"),
                unit_price_components=[
                    make_price_component(
                        amount=Decimal(MAX_VALID_VALUE), code=make_coding("test-base")
                    )
                ],
            )
        )
        self.assertEqual(spec.unit_price_components[0].amount, Decimal(MAX_VALID_VALUE))

    # ChargeItem model persistence and read serialization.

    def test_charge_item_model_validation(self):
        """A charge item with valid relations is persisted."""
        charge_item = self.create_charge_item(title="Test Charge Item")
        self.assertIsNotNone(charge_item.id)

    def test_charge_item_foreign_key_constraints(self):
        """A charge item pointing to a non-existent patient fails validation."""
        with self.assertRaises((IntegrityError, ValidationError)):
            charge_item = self.build_charge_item(patient=None)
            charge_item.patient_id = 99999
            charge_item.full_clean()
            charge_item.save()

    def test_charge_item_cancelled_status_transitions(self):
        """Charge items can be stored with each cancelled status."""
        for cancelled_status in CHARGE_ITEM_CANCELLED_STATUS:
            charge_item = self.create_charge_item(
                title="Test Charge Item",
                status=cancelled_status,
                unit_price_components=[],
                total_price_components=[],
            )

            self.assertEqual(charge_item.status, cancelled_status)
            self.assertIn(charge_item.status, CHARGE_ITEM_CANCELLED_STATUS)

    def test_charge_item_read_spec_serialization(self):
        """The read spec serializes a charge item with its title and external id."""
        charge_item = self.create_charge_item(
            title="Test Charge Item",
            unit_price_components=[],
            total_price_components=[],
        )

        serialized = ChargeItemReadSpec.serialize(charge_item)
        self.assertEqual(serialized.title, "Test Charge Item")
        self.assertEqual(serialized.id, charge_item.external_id)

    # Total price calculation in sync_charge_item_costs.

    def test_nonzero_amount_components_still_work(self):
        """
        Verify that non-zero discount and tax amounts are correctly calculated.
        """
        self.assert_synced_total(
            [
                make_price_component(),
                make_price_component("tax", amount="10.00"),
                make_price_component("discount", amount="5.00"),
            ],
            "105.00",
        )

    def test_factor_based_components_still_work(self):
        """
        Sanity check that non-zero factor-based (percentage) components, which were already handled correctly.
        """
        self.assert_synced_total(
            [
                make_price_component(),
                make_price_component("tax", amount=None, factor="10.00"),
            ],
            "110.00",
        )

    def test_zero_amount_tax_component_does_not_raise(self):
        """
        Verify that a tax component with amount=0 does not raise and contributes 0.
        """
        self.assert_synced_total(
            [make_price_component(), make_price_component("tax", amount="0.00")],
            "100.00",
        )

    def test_zero_amount_surcharge_component_does_not_raise(self):
        """
        Verify that a surcharge component with amount=0 does not raise and contributes 0.
        """
        self.assert_synced_total(
            [make_price_component(), make_price_component("surcharge", amount="0.00")],
            "100.00",
        )

    def test_zero_amount_discount_component_does_not_raise(self):
        """
        Verify that a discount component with amount=0 does not raise and contributes 0.
        """
        self.assert_synced_total(
            [make_price_component(), make_price_component("discount", amount="0.00")],
            "100.00",
        )

    def test_zero_factor_component_does_not_raise(self):
        """
        A tax component with factor=0 (e.g. a 0% tax bracket) should
        compute to a zero contribution, not raise "Amount or factor is
        required". This mirrors the amount=0 cases above but exercises
        the `factor` branch of `calculate_amount` specifically, since
        `factor=0` was just as broken as `amount=0` by the original
        truthy check.
        """
        self.assert_synced_total(
            [
                make_price_component(),
                make_price_component("tax", amount=None, factor="0"),
            ],
            "100.00",
        )

    def test_missing_amount_and_factor_still_raises(self):
        """
        Verify that a component missing both amount and factor raises Pydantic ValidationError.
        """
        charge_item = self.build_charge_item(
            unit_price_components=[
                make_price_component(),
                make_price_component("tax", amount=None),
            ]
        )
        with self.assertRaises(PydanticValidationError):
            sync_charge_item_costs(charge_item)
