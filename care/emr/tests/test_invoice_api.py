from decimal import Decimal

from django.urls import reverse
from model_bakery import baker
from rest_framework import status

from care.emr.models import Account
from care.emr.resources.account.spec import (
    AccountBillingStatusOptions,
    AccountStatusOptions,
)
from care.emr.resources.charge_item.spec import ChargeItemStatusOptions
from care.emr.resources.invoice.spec import InvoiceStatusOptions
from care.security.permissions.invoice import InvoicePermissions
from care.utils.tests.base import CareAPITestBase


class TestAttachAccountToInvoice(CareAPITestBase):
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

        self.charge_item_1 = baker.make(
            "emr.ChargeItem",
            facility=self.facility,
            patient=self.patient,
            encounter=self.encounter,
            account=self.account,
            status=ChargeItemStatusOptions.billable.value,
            quantity=Decimal("1.00"),
            unit_price_components=[{"amount": 100, "monetary_component_type": "base"}],
            total_price_components=[{"amount": 100, "monetary_component_type": "base"}],
            total_price=Decimal("100.00"),
        )
        self.charge_item_2 = baker.make(
            "emr.ChargeItem",
            facility=self.facility,
            patient=self.patient,
            encounter=self.encounter,
            account=self.account,
            status=ChargeItemStatusOptions.billable.value,
            quantity=Decimal("1.00"),
            unit_price_components=[{"amount": 200, "monetary_component_type": "base"}],
            total_price_components=[{"amount": 200, "monetary_component_type": "base"}],
            total_price=Decimal("200.00"),
        )

    def _get_url(self, invoice_external_id):
        return reverse(
            "invoice-attach-account-to-invoice",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": invoice_external_id,
            },
        )

    def test_attach_account_to_invoice_attaches_all_billable_charge_items(self):
        role = self.create_role_with_permissions(
            [
                InvoicePermissions.can_read_invoice.name,
                InvoicePermissions.can_write_invoice.name,
            ]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        invoice = baker.make(
            "emr.Invoice",
            facility=self.facility,
            account=self.account,
            patient=self.patient,
            status=InvoiceStatusOptions.draft.value,
            total_net=Decimal("0.00"),
            total_gross=Decimal("0.00"),
        )

        response = self.client.post(self._get_url(invoice.external_id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        invoice.refresh_from_db()
        # Assert invoice.charge_items is a proper Python list, not a queryset
        self.assertIsInstance(invoice.charge_items, list)
        self.assertEqual(len(invoice.charge_items), 2)
        self.assertIn(self.charge_item_1.id, invoice.charge_items)
        self.assertIn(self.charge_item_2.id, invoice.charge_items)

        # Assert charge items status updated to billed and paid_invoice set
        self.charge_item_1.refresh_from_db()
        self.charge_item_2.refresh_from_db()
        self.assertEqual(
            self.charge_item_1.status, ChargeItemStatusOptions.billed.value
        )
        self.assertEqual(
            self.charge_item_2.status, ChargeItemStatusOptions.billed.value
        )
        self.assertEqual(self.charge_item_1.paid_invoice, invoice)
        self.assertEqual(self.charge_item_2.paid_invoice, invoice)

    def test_attach_account_to_invoice_rejects_negative_total_without_refund(self):
        role = self.create_role_with_permissions(
            [
                InvoicePermissions.can_read_invoice.name,
                InvoicePermissions.can_write_invoice.name,
            ]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        baker.make(
            "emr.ChargeItem",
            facility=self.facility,
            patient=self.patient,
            encounter=self.encounter,
            account=self.account,
            status=ChargeItemStatusOptions.billable.value,
            quantity=Decimal("1.00"),
            unit_price_components=[{"amount": -500, "monetary_component_type": "base"}],
            total_price_components=[
                {"amount": -500, "monetary_component_type": "base"}
            ],
            total_price=Decimal("-500.00"),
        )

        invoice = baker.make(
            "emr.Invoice",
            facility=self.facility,
            account=self.account,
            patient=self.patient,
            status=InvoiceStatusOptions.draft.value,
            is_refund=False,
            total_net=Decimal("0.00"),
            total_gross=Decimal("0.00"),
        )

        response = self.client.post(self._get_url(invoice.external_id))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["errors"][0]["msg"],
            "A Refund Invoice is required for negative values",
        )

    def test_attach_account_to_invoice_requires_draft_status(self):
        role = self.create_role_with_permissions(
            [
                InvoicePermissions.can_read_invoice.name,
                InvoicePermissions.can_write_invoice.name,
            ]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(user=self.user)

        invoice = baker.make(
            "emr.Invoice",
            facility=self.facility,
            account=self.account,
            patient=self.patient,
            status=InvoiceStatusOptions.issued.value,
        )

        response = self.client.post(self._get_url(invoice.external_id))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_attach_account_to_invoice_without_permission(self):
        # Authenticate without attaching the role with permissions to the user
        self.client.force_authenticate(user=self.user)

        invoice = baker.make(
            "emr.Invoice",
            facility=self.facility,
            account=self.account,
            patient=self.patient,
            status=InvoiceStatusOptions.draft.value,
        )

        response = self.client.post(self._get_url(invoice.external_id))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
