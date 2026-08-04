import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse
from model_bakery import baker

from care.emr.models import Account, ChargeItem, ChargeItemDefinition
from care.emr.models.facility_config import FacilityMonetoryConfig
from care.emr.models.payment_reconciliation import PaymentReconciliation
from care.emr.resources.account.spec import (
    AccountBillingStatusOptions,
    AccountStatusOptions,
)
from care.emr.resources.charge_item.spec import ChargeItemStatusOptions
from care.emr.resources.charge_item_definition.spec import (
    ChargeItemDefinitionStatusOptions,
)
from care.emr.resources.invoice.spec import InvoiceStatusOptions
from care.emr.resources.invoice.sync_items import sync_invoice_items
from care.emr.signals.patient.facility_name_identifier import (
    FacilityPatientNameIdentifierConfig,
)
from care.emr.signals.patient.name_identifier import NameIdentifierConfig
from care.emr.signals.patient.phone_number_identifier import PhoneNumberIdentifierConfig
from care.security.permissions.invoice import InvoicePermissions
from care.utils.lock import ObjectLocked
from care.utils.tests.base import CareAPITestBase


class InvoiceAPITestBase(CareAPITestBase):
    def setUp(self):
        NameIdentifierConfig.CACHED_CONFIG = {}
        PhoneNumberIdentifierConfig.CACHED_CONFIG = {}
        FacilityPatientNameIdentifierConfig.CACHED_CONFIG = {}
        self.user = self.create_user()
        self.superuser = self.create_super_user()
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
        self.charge_item = self.create_charge_item()
        self.url = reverse(
            "invoice-list",
            kwargs={"facility_external_id": self.facility.external_id},
        )
        permissions = [
            InvoicePermissions.can_read_invoice.name,
            InvoicePermissions.can_write_invoice.name,
        ]
        self.role = self.create_role_with_permissions(permissions)

    def generate_invoice_data(self, **kwargs):
        data = {
            "account": self.account.external_id,
            "status": kwargs.get("status", InvoiceStatusOptions.draft.value),
            "charge_items": kwargs.get("charge_items", [self.charge_item.external_id]),
            "title": "Test Invoice",
            "number": f"INV-{random.randint(1000, 9999)}",  # noqa: S311
            "issue_date": datetime.now(UTC).isoformat(),
        }
        data.update(**kwargs)
        return data

    def create_invoice(self, **kwargs):
        invoice = baker.make(
            "emr.Invoice",
            facility=self.facility,
            account=self.account,
            patient=self.patient,
            status=kwargs.get("status", InvoiceStatusOptions.draft.value),
            charge_items=kwargs.get("charge_items", [self.charge_item.id]),
            title=kwargs.get("title", "Test Invoice"),
            number=kwargs.get("number", f"INV-{random.randint(1000, 9999)}"),  # noqa: S311
            issue_date=kwargs.get("issue_date", datetime.now(UTC).isoformat()),
            locked=kwargs.get("locked", False),
        )
        sync_invoice_items(invoice)
        invoice.save()
        return invoice

    def get_detail_url(self, external_id):
        return reverse(
            "invoice-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": external_id,
            },
        )

    def create_charge_item(self, **kwargs):
        data = {
            "title": self.fake.sentence(nb_words=4),
            "patient": self.patient,
            "encounter": self.encounter,
            "account": self.account,
            "charge_item_definition": self.charge_item_definition,
            "facility": self.facility,
            "status": kwargs.get("status", ChargeItemStatusOptions.billable.value),
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

    # testcases for create invoice with charge items and account

    def test_create_invoice_with_superuser(self):
        """
        Test creating an invoice with a superuser.
        """
        self.client.force_authenticate(user=self.superuser)
        data = self.generate_invoice_data()
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 200)
        response_data = response.data
        self.assertEqual(response_data["account"]["id"], str(self.account.external_id))
        self.assertEqual(response_data["status"], InvoiceStatusOptions.draft.value)
        self.assertEqual(len(response_data["charge_items"]), 1)
        self.assertEqual(
            response_data["charge_items"][0]["id"], str(self.charge_item.external_id)
        )
        self.assertEqual(
            Decimal(response_data["total_net"]), self.charge_item.total_price
        )
        self.assertEqual(
            Decimal(response_data["total_gross"]), self.charge_item.total_price
        )

    def test_create_invoice_without_number_auto_generates(self):
        """
        Test that omitting number triggers auto-generation via the configured expression.
        """
        config = FacilityMonetoryConfig.get_monetory_config(self.facility.id)
        config.invoice_number_expression = (
            "f'INV-{invoice_count + 1}-{current_year_yy}'"
        )
        config.save()
        self.client.force_authenticate(user=self.superuser)
        data = self.generate_invoice_data()
        data.pop("number")
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["number"])

    def test_create_invoice_fails_when_create_lock_is_held(self):
        """
        Test that invoice creation returns a validation error when the global create lock is held.
        """
        self.client.force_authenticate(user=self.superuser)
        data = self.generate_invoice_data()
        with patch(
            "care.emr.api.viewsets.invoice.InvoiceCreateLock.__enter__",
            side_effect=ObjectLocked,
        ):
            response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["errors"][0]["msg"], "Invoice creation failed")

    def test_create_invoice_with_user_without_permission(self):
        """
        Test creating an invoice with a user without write permission.
        """
        self.client.force_authenticate(user=self.user)
        data = self.generate_invoice_data()
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Cannot write invoice")

    def test_create_invoice_with_user_with_permission(self):
        """
        Test creating an invoice with a user with write permission.
        """
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        data = self.generate_invoice_data()
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 200)
        response_data = response.data
        self.assertEqual(response_data["account"]["id"], str(self.account.external_id))
        self.assertEqual(response_data["status"], InvoiceStatusOptions.draft.value)
        self.assertEqual(len(response_data["charge_items"]), 1)
        self.assertEqual(
            response_data["charge_items"][0]["id"], str(self.charge_item.external_id)
        )
        self.assertEqual(
            Decimal(response_data["total_net"]), self.charge_item.total_price
        )
        self.assertEqual(
            Decimal(response_data["total_gross"]), self.charge_item.total_price
        )

    def test_create_invoice_with_account_from_other_facility(self):
        """
        Test creating an invoice with an account that belongs to another facility.
        """
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        another_account = Account.objects.create(
            facility=self.create_facility(user=self.user),
            patient=self.patient,
            name=f"Account for {self.patient.name}",
        )
        self.client.force_authenticate(user=self.user)
        data = self.generate_invoice_data(account=str(another_account.external_id))
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "Account is not associated with the facility",
        )

        # testcases for update invoice

    def test_update_invoice_with_superuser(self):
        """
        Test updating an invoice with a superuser.
        """
        self.client.force_authenticate(user=self.superuser)
        invoice = self.create_invoice()
        data = self.generate_invoice_data(title="Updated Invoice Title")
        response = self.client.put(
            self.get_detail_url(invoice.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.data
        self.assertEqual(response_data["title"], "Updated Invoice Title")

    def test_update_invoice_with_user_without_write_permission(self):
        """
        Test updating an invoice with a user without write permission.
        """
        self.client.force_authenticate(user=self.user)
        permissions = [
            InvoicePermissions.can_read_invoice.name,
        ]
        self.role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        invoice = self.create_invoice()
        data = self.generate_invoice_data(title="Updated Invoice Title")
        response = self.client.put(
            self.get_detail_url(invoice.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Cannot write invoice")

    def test_update_invoice_with_user_with_permission(self):
        """
        Test updating an invoice with a user with write permission.
        """
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        invoice = self.create_invoice(status=InvoiceStatusOptions.draft.value)
        data = self.generate_invoice_data(title="Updated Invoice Title")
        response = self.client.put(
            self.get_detail_url(invoice.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.data
        self.assertEqual(response_data["title"], "Updated Invoice Title")

    def test_update_invoice_with_cancelled_status(self):
        """
        Test updating an invoice that is already cancelled.
        """
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        invoice = self.create_invoice(status=InvoiceStatusOptions.cancelled.value)
        data = self.generate_invoice_data(title="Updated Invoice Title")
        response = self.client.put(
            self.get_detail_url(invoice.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["errors"][0]["msg"], "Invoice is already cancelled"
        )

    def test_update_invoice_to_cancelled_status(self):
        """
        Test updating an invoice to cancelled status.
        """
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        invoice = self.create_invoice()
        data = self.generate_invoice_data(status=InvoiceStatusOptions.cancelled.value)
        response = self.client.put(
            self.get_detail_url(invoice.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 400)
        response_data = response.data
        self.assertEqual(
            response_data["errors"][0]["msg"],
            "Call the cancel invoice API to cancel the invoice",
        )

    def test_update_invoice_with_no_charge_items_and_issued_status(self):
        """
        Test updating an invoice with no charge items and issued status.
        """
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        invoice = self.create_invoice(charge_items=[])
        data = self.generate_invoice_data(status=InvoiceStatusOptions.issued.value)
        response = self.client.put(
            self.get_detail_url(invoice.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 400)
        response_data = response.data
        self.assertEqual(
            response_data["errors"][0]["msg"],
            "Invoice must have at least one charge item",
        )

    def test_update_issued_invoice_to_draft_status(self):
        """
        Test updating an issued invoice to draft status.
        """
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        invoice = self.create_invoice(status=InvoiceStatusOptions.issued.value)
        data = self.generate_invoice_data(status=InvoiceStatusOptions.draft.value)
        response = self.client.put(
            self.get_detail_url(invoice.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 400)
        response_data = response.data
        self.assertEqual(response_data["errors"][0]["msg"], "Invoice is already issued")

    def test_update_balanced_invoice(self):
        """
        Test updating a balanced invoice.
        """
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        invoice = self.create_invoice(status=InvoiceStatusOptions.balanced.value)
        data = self.generate_invoice_data(title="Updated Invoice Title")
        response = self.client.put(
            self.get_detail_url(invoice.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 400)
        response_data = response.data
        self.assertEqual(
            response_data["errors"][0]["msg"], "Invoice is already balanced"
        )

    def test_update_invoice_from_draft_to_balanced_status(self):
        """
        Test updating an invoice from draft to balanced status.
        """
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        invoice = self.create_invoice()
        data = self.generate_invoice_data(status=InvoiceStatusOptions.balanced.value)
        response = self.client.put(
            self.get_detail_url(invoice.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 400)
        response_data = response.data
        self.assertEqual(
            response_data["errors"][0]["msg"],
            "Invoice needs to be issued before balancing",
        )

    def test_update_invoice_from_issued_to_balanced_status(self):
        """
        Test updating an invoice from issued to balanced status.
        """
        self.client.force_authenticate(user=self.superuser)
        charge_item = self.create_charge_item(
            status=ChargeItemStatusOptions.billed.value
        )

        invoice = self.create_invoice(
            status=InvoiceStatusOptions.issued.value, charge_items=[charge_item.id]
        )
        data = self.generate_invoice_data(
            status=InvoiceStatusOptions.balanced.value,
            charge_items=[charge_item.external_id],
        )
        response = self.client.put(
            self.get_detail_url(invoice.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.data
        self.assertEqual(response_data["status"], InvoiceStatusOptions.balanced.value)

    def test_update_invoice_from_draft_to_issued_status(self):
        """
        Test updating an invoice from draft to issued status.
        """
        self.client.force_authenticate(user=self.superuser)
        invoice = self.create_invoice(status=InvoiceStatusOptions.draft.value)
        data = self.generate_invoice_data(
            status=InvoiceStatusOptions.issued.value,
            charge_items=[self.charge_item.external_id],
        )
        response = self.client.put(
            self.get_detail_url(invoice.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], InvoiceStatusOptions.issued.value)

    # Testcase for listing invoices

    def test_list_invoices_with_superuser(self):
        """
        Test listing invoices with a superuser.
        """
        self.client.force_authenticate(user=self.superuser)
        invoice = self.create_invoice()
        response = self.client.get(self.url, format="json")
        self.assertEqual(response.status_code, 200)
        response_data = response.data["results"]
        self.assertEqual(len(response_data), 1)
        self.assertEqual(response_data[0]["id"], str(invoice.external_id))

    def test_list_invoices_with_user_without_permission(self):
        """
        Test listing invoices with a user without read permission.
        """
        permissions = [
            InvoicePermissions.can_write_invoice.name,
        ]
        self.role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        self.create_invoice()
        response = self.client.get(self.url, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Cannot read invoice")

    def test_list_invoices_with_user_with_permission(self):
        """
        Test listing invoices with a user with read permission.
        """
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        invoice = self.create_invoice()
        response = self.client.get(self.url, format="json")
        self.assertEqual(response.status_code, 200)
        response_data = response.data["results"]
        self.assertEqual(len(response_data), 1)
        self.assertEqual(response_data[0]["id"], str(invoice.external_id))

    def test_list_invoices_with_only_payment_reconciliation_present_filter(self):
        """
        Test listing invoices with only the payment_reconciliation_present filter.
        """
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        invoice = self.create_invoice()
        # Create a payment reconciliation for the invoice
        PaymentReconciliation.objects.create(
            facility=self.facility,
            account=self.account,
            status="completed",
            amount=invoice.total_gross,
            tendered_amount=invoice.total_gross,
            returned_amount=Decimal("0.00"),
            target_invoice=invoice,
        )
        response = self.client.get(
            f"{self.url}?payment_reconciliation_present=true", format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "Account is required when payment reconciliation filter is present",
        )

    def test_list_invoices_with_payment_reconciliation_present_filter_and_account(self):
        """
        Test listing invoices with the payment_reconciliation_present filter and an account.
        """
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        invoice = self.create_invoice()
        # Create a payment reconciliation for the invoice
        PaymentReconciliation.objects.create(
            facility=self.facility,
            account=self.account,
            status="completed",
            amount=invoice.total_gross,
            tendered_amount=invoice.total_gross,
            returned_amount=Decimal("0.00"),
            target_invoice=invoice,
        )
        response = self.client.get(
            f"{self.url}?payment_reconciliation_present=true&account={self.account.external_id}",
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.data["results"]
        self.assertEqual(len(response_data), 1)
        self.assertEqual(response_data[0]["id"], str(invoice.external_id))

    def test_list_invoices_with_account_filter(self):
        """
        Test listing invoices with an account filter.
        """
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        invoice = self.create_invoice()
        response = self.client.get(
            f"{self.url}?payment_reconciliation_present=false&account={self.account.external_id}",
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.data["results"]
        self.assertEqual(len(response_data), 1)
        self.assertEqual(response_data[0]["id"], str(invoice.external_id))

    # Testcases for retrieve api

    def test_retrieve_invoice_with_superuser(self):
        """
        Test retrieving an invoice with a superuser.
        """
        self.client.force_authenticate(user=self.superuser)
        invoice = self.create_invoice()
        response = self.client.get(
            self.get_detail_url(invoice.external_id), format="json"
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.data
        self.assertEqual(response_data["id"], str(invoice.external_id))

    def test_retrieve_invoice_with_user_without_permission(self):
        """
        Test retrieving an invoice with a user without read permission.
        """
        permissions = [
            InvoicePermissions.can_write_invoice.name,
        ]
        self.role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        invoice = self.create_invoice()
        response = self.client.get(
            self.get_detail_url(invoice.external_id), format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Cannot read invoice")

    def test_retrieve_invoice_with_user_with_permission(self):
        """
        Test retrieving an invoice with a user with read permission.
        """
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        invoice = self.create_invoice()
        response = self.client.get(
            self.get_detail_url(invoice.external_id), format="json"
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.data
        self.assertEqual(response_data["id"], str(invoice.external_id))

    def test_retrieve_invoice_with_payment_reconciliation_present_and_account_filter(
        self,
    ):
        """
        Test retrieving an invoice with the payment_reconciliation_present and account filter.
        """
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        invoice = self.create_invoice()
        # Create a payment reconciliation for the invoice
        PaymentReconciliation.objects.create(
            facility=self.facility,
            account=self.account,
            status="completed",
            amount=invoice.total_gross,
            tendered_amount=invoice.total_gross,
            returned_amount=Decimal("0.00"),
            target_invoice=invoice,
        )
        response = self.client.get(
            f"{self.get_detail_url(invoice.external_id)}?payment_reconciliation_present=true&account={self.account.external_id}",
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.data
        self.assertEqual(response_data["id"], str(invoice.external_id))

    def test_retrieve_invoice_with_only_payment_reconciliation_present(self):
        """
        Test retrieving an invoice with only the payment_reconciliation_present filter.
        """
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        invoice = self.create_invoice()
        # Create a payment reconciliation for the invoice
        PaymentReconciliation.objects.create(
            facility=self.facility,
            account=self.account,
            status="completed",
            amount=invoice.total_gross,
            tendered_amount=invoice.total_gross,
            returned_amount=Decimal("0.00"),
            target_invoice=invoice,
        )
        response = self.client.get(
            f"{self.get_detail_url(invoice.external_id)}?payment_reconciliation_present=true",
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "Account is required when payment reconciliation filter is present",
        )

    def test_retrieve_invoice_with_account_filter(self):
        """
        Test retrieving an invoice with an account filter.
        """
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        invoice = self.create_invoice()
        response = self.client.get(
            f"{self.get_detail_url(invoice.external_id)}?payment_reconciliation_present=false&account={self.account.external_id}",
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.data
        self.assertEqual(response_data["id"], str(invoice.external_id))

    def test_retrive_locked_invoice_with_superuser(self):
        """
        Test retrieving a locked invoice with a superuser.
        """
        self.client.force_authenticate(user=self.superuser)
        invoice = self.create_invoice(locked=True)
        response = self.client.get(
            self.get_detail_url(invoice.external_id), format="json"
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.data
        self.assertEqual(response_data["id"], str(invoice.external_id))

    def test_retrive_locked_invoice_with_user_without_permission(self):
        """
        Test retrieving a locked invoice with a user without read permission.
        """
        permissions = [
            InvoicePermissions.can_read_invoice.name,
        ]
        self.role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        invoice = self.create_invoice(locked=True)
        response = self.client.get(
            self.get_detail_url(invoice.external_id), format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Locked invoice permission denied.")

    def test_retrive_locked_invoice_with_user_with_permission(self):
        """
        Test retrieving a locked invoice with a user with locked invoice management permission.
        """
        permissions = [
            InvoicePermissions.can_read_invoice.name,
            InvoicePermissions.can_manage_locked_invoice.name,
        ]
        self.role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        invoice = self.create_invoice(locked=True)
        response = self.client.get(
            self.get_detail_url(invoice.external_id), format="json"
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.data
        self.assertEqual(response_data["id"], str(invoice.external_id))

    # Testcases for cancel invoice api

    def cancel_invoice(self, external_id, reason):
        """
        Helper method to cancel an invoice.
        """
        url = reverse(
            "invoice-cancel-invoice",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": external_id,
            },
        )
        data = {"reason": reason}
        return self.client.post(url, data, format="json")

    def test_cancel_invoice_with_superuser(self):
        """
        Test cancelling an invoice with a superuser.
        """
        self.client.force_authenticate(user=self.superuser)
        invoice = self.create_invoice()
        response = self.cancel_invoice(
            invoice.external_id, InvoiceStatusOptions.cancelled.value
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.data
        self.assertEqual(response_data["status"], InvoiceStatusOptions.cancelled.value)

    def test_cancel_invoice_with_user_without_permission(self):
        """
        Test cancelling an invoice with a user without write permission.
        """
        permissions = [
            InvoicePermissions.can_read_invoice.name,
        ]
        self.role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        invoice = self.create_invoice()
        response = self.cancel_invoice(
            invoice.external_id, InvoiceStatusOptions.cancelled.value
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Cannot cancel invoice")

    @override_settings(INVOICE_FREE_CANCEL_PERIOD_MINUTES=5)
    def test_cancel_invoice_with_user_with_permission_within_period(self):
        """
        Test cancelling an invoice with a user with write permission.
        """
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        invoice = self.create_invoice()
        response = self.cancel_invoice(
            invoice.external_id, InvoiceStatusOptions.cancelled.value
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.data
        self.assertEqual(response_data["status"], InvoiceStatusOptions.cancelled.value)

    def test_cancel_invoice_with_already_cancelled_invoice(self):
        """
        Test cancelling an invoice that is already cancelled.
        """
        self.client.force_authenticate(user=self.superuser)
        invoice = self.create_invoice(status=InvoiceStatusOptions.cancelled.value)
        response = self.cancel_invoice(
            invoice.external_id, InvoiceStatusOptions.cancelled.value
        )
        self.assertEqual(response.status_code, 400)
        response_data = response.data
        self.assertEqual(
            response_data["errors"][0]["msg"], "Invoice is already cancelled"
        )

    @override_settings(INVOICE_FREE_CANCEL_PERIOD_MINUTES=5)
    def test_cancel_invoice_with_user_with_permission_outside_period(self):
        """
        Test cancelling an invoice with a user with write permission outside the free cancel period.
        """
        permissions = [
            InvoicePermissions.can_destroy_invoice.name,
            InvoicePermissions.can_read_invoice.name,
        ]
        self.role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        invoice = self.create_invoice()
        # Manually set the issue_date to be outside the free cancel period
        invoice.created_date = datetime.now(UTC) - timedelta(minutes=10)
        invoice.save()
        response = self.cancel_invoice(
            invoice.external_id, InvoiceStatusOptions.cancelled.value
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], InvoiceStatusOptions.cancelled.value)

    def test_cancel_invoice_with_user_without_permission_outside_period(self):
        """
        Test cancelling an invoice with a user without write permission outside the free cancel period.
        """
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        invoice = self.create_invoice()
        # Manually set the issue_date to be outside the free cancel period
        invoice.created_date = datetime.now(UTC) - timedelta(minutes=10)
        invoice.save()
        response = self.cancel_invoice(
            invoice.external_id, InvoiceStatusOptions.cancelled.value
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Cannot cancel invoice")

    # def testcases for attach and detach charge items to invoice

    def get_attach_charge_items_url(self, external_id):
        return reverse(
            "invoice-attach-items-to-invoice",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": external_id,
            },
        )

    def get_remove_charge_items_url(self, external_id):
        return reverse(
            "invoice-remove-item-from-invoice",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": external_id,
            },
        )

    def test_attach_charge_items_to_invoice_with_superuser(self):
        """
        Test attaching charge items to an invoice with a superuser.
        """
        self.client.force_authenticate(user=self.superuser)
        invoice = self.create_invoice()
        new_charge_item = self.create_charge_item()
        url = self.get_attach_charge_items_url(invoice.external_id)
        data = {"charge_items": [str(new_charge_item.external_id)]}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        response_data = response.data
        self.assertEqual(len(response_data["charge_items"]), 2)
        self.assertIn(
            str(new_charge_item.external_id),
            [str(item["id"]) for item in response_data["charge_items"]],
        )

    def test_attach_charge_items_to_invoice_with_user_without_permission(self):
        """
        Test attaching charge items to an invoice with a user without write permission.
        """
        permissions = [
            InvoicePermissions.can_read_invoice.name,
        ]
        self.role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        invoice = self.create_invoice()
        new_charge_item = self.create_charge_item()
        url = self.get_attach_charge_items_url(invoice.external_id)
        data = {"charge_items": [str(new_charge_item.external_id)]}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Cannot write invoice")

    def test_attach_charge_items_to_invoice_with_user_with_permission(self):
        """
        Test attaching charge items to an invoice with a user with write permission.
        """
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        invoice = self.create_invoice()
        new_charge_item = self.create_charge_item()
        url = self.get_attach_charge_items_url(invoice.external_id)
        data = {"charge_items": [str(new_charge_item.external_id)]}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        response_data = response.data
        self.assertEqual(len(response_data["charge_items"]), 2)
        self.assertIn(
            str(new_charge_item.external_id),
            [str(item["id"]) for item in response_data["charge_items"]],
        )

    def test_remove_charge_items_from_invoice_with_superuser(self):
        """
        Test removing charge items from an invoice with a superuser.
        """
        self.client.force_authenticate(user=self.superuser)
        invoice = self.create_invoice()
        url = self.get_remove_charge_items_url(invoice.external_id)
        data = {"charge_item": str(self.charge_item.external_id)}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        response_data = response.data
        self.assertEqual(len(response_data["charge_items"]), 0)

    def test_remove_charge_items_from_invoice_with_user_without_permission(self):
        """
        Test removing charge items from an invoice with a user without write permission.
        """
        permissions = [
            InvoicePermissions.can_read_invoice.name,
        ]
        self.role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        invoice = self.create_invoice()
        url = self.get_remove_charge_items_url(invoice.external_id)
        data = {"charge_item": str(self.charge_item.external_id)}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Cannot write invoice")

    def test_remove_charge_items_from_invoice_with_user_with_permission(self):
        """
        Test removing charge items from an invoice with a user with write permission.
        """
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        invoice = self.create_invoice()
        url = self.get_remove_charge_items_url(invoice.external_id)
        data = {"charge_item": str(self.charge_item.external_id)}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        response_data = response.data
        self.assertEqual(len(response_data["charge_items"]), 0)

    def test_remove_charge_items_from_invoice_non_draft_status(self):
        """
        Test removing charge items from an invoice with a non-draft status.
        """
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        invoice = self.create_invoice(status=InvoiceStatusOptions.issued.value)
        url = self.get_remove_charge_items_url(invoice.external_id)
        data = {"charge_item": str(self.charge_item.external_id)}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 400)
        response_data = response.data
        self.assertEqual(
            response_data["errors"][0]["msg"],
            "Invoice is not in draft",
        )

    def test_attach_charge_items_to_invoice_non_draft_status(self):
        """
        Test attaching charge items to an invoice with a non-draft status.
        """
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        invoice = self.create_invoice(status=InvoiceStatusOptions.issued.value)
        new_charge_item = self.create_charge_item()
        url = self.get_attach_charge_items_url(invoice.external_id)
        data = {"charge_items": [str(new_charge_item.external_id)]}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 400)
        response_data = response.data
        self.assertEqual(
            response_data["errors"][0]["msg"],
            "Invoice is not in draft",
        )

    def test_remove_charge_items_from_invoice_with_non_related_charge_item(self):
        """
        Test removing charge items from an invoice with a non-existent charge item.
        """
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        invoice = self.create_invoice()
        charge_item = self.create_charge_item()
        url = self.get_remove_charge_items_url(invoice.external_id)
        data = {"charge_item": str(charge_item.external_id)}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 400)
        response_data = response.data
        self.assertEqual(
            response_data["errors"][0]["msg"],
            "Charge item not found in invoice",
        )

    # Testcases for invoice lock and unlock

    def get_lock_invoice_url(self, external_id):
        return reverse(
            "invoice-lock",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": external_id,
            },
        )

    def get_unlock_invoice_url(self, external_id):
        return reverse(
            "invoice-unlock",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": external_id,
            },
        )

    def test_lock_invoice_with_superuser(self):
        """
        Test locking an invoice with a superuser.
        """
        self.client.force_authenticate(user=self.superuser)
        invoice = self.create_invoice()
        url = self.get_lock_invoice_url(invoice.external_id)
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, 200)
        response_data = response.data
        self.assertTrue(response_data["locked"])

    def test_lock_invoice_with_user_without_permission(self):
        """
        Test locking an invoice with a user without write permission.
        """
        permissions = [
            InvoicePermissions.can_read_invoice.name,
        ]
        self.role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        invoice = self.create_invoice()
        url = self.get_lock_invoice_url(invoice.external_id)
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Locked invoice permission denied.")

    def test_lock_invoice_with_user_with_permission(self):
        """
        Test locking an invoice with a user with write permission.
        """
        permissions = [
            InvoicePermissions.can_read_invoice.name,
            InvoicePermissions.can_manage_locked_invoice.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)
        invoice = self.create_invoice()
        url = self.get_lock_invoice_url(invoice.external_id)
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, 200)
        response_data = response.data
        self.assertTrue(response_data["locked"])

    def test_lock_invoice_with_already_locked_invoice(self):
        """
        Test locking an invoice that is already locked.
        """
        self.client.force_authenticate(user=self.superuser)
        invoice = self.create_invoice(locked=True)
        url = self.get_lock_invoice_url(invoice.external_id)
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, 400)
        response_data = response.data
        self.assertEqual(
            response_data["errors"][0]["msg"],
            "Invoice is already locked",
        )

    def test_unlock_invoice_with_superuser(self):
        """
        Test unlocking an invoice with a superuser.
        """
        self.client.force_authenticate(user=self.superuser)
        invoice = self.create_invoice(locked=True)
        url = self.get_unlock_invoice_url(invoice.external_id)
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, 200)
        response_data = response.data
        self.assertFalse(response_data["locked"])

    def test_unlock_invoice_with_user_without_permission(self):
        """
        Test unlocking an invoice with a user without write permission.
        """
        permissions = [
            InvoicePermissions.can_read_invoice.name,
        ]
        self.role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(
            self.organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        invoice = self.create_invoice(locked=True)
        url = self.get_unlock_invoice_url(invoice.external_id)
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Locked invoice permission denied.")

    def test_unlock_invoice_with_user_with_permission(self):
        """
        Test unlocking an invoice with a user with write permission.
        """
        permissions = [
            InvoicePermissions.can_read_invoice.name,
            InvoicePermissions.can_manage_locked_invoice.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)
        invoice = self.create_invoice(locked=True)
        url = self.get_unlock_invoice_url(invoice.external_id)
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, 200)
        response_data = response.data
        self.assertFalse(response_data["locked"])

    def test_unlock_invoice_with_already_unlocked_invoice(self):
        """
        Test unlocking an invoice that is already unlocked.
        """
        self.client.force_authenticate(user=self.superuser)
        invoice = self.create_invoice(locked=False)
        url = self.get_unlock_invoice_url(invoice.external_id)
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, 400)
        response_data = response.data
        self.assertEqual(
            response_data["errors"][0]["msg"],
            "Invoice is not locked",
        )
