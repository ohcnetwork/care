from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from django.urls import reverse
from model_bakery import baker
from rest_framework import status
from rest_framework.exceptions import ValidationError

from care.emr.api.viewsets.invoice import InvoiceViewSet
from care.emr.models.account import Account
from care.emr.models.charge_item import ChargeItem
from care.emr.models.invoice import Invoice
from care.emr.resources.account.spec import (
    AccountBillingStatusOptions,
    AccountStatusOptions,
)
from care.emr.resources.charge_item.handle_charge_item_cancel import (
    handle_charge_item_cancel,
)
from care.emr.resources.charge_item.spec import ChargeItemStatusOptions
from care.emr.resources.invoice.spec import InvoiceStatusOptions
from care.emr.resources.invoice.sync_items import sync_invoice_items
from care.utils.tests.base import CareAPITestBase


class InvoiceChargeItemOwnershipTests(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_super_user()
        self.facility = self.create_facility(user=self.user)
        self.patient = self.create_patient()
        self.account = baker.make(
            Account,
            facility=self.facility,
            patient=self.patient,
            status=AccountStatusOptions.active.value,
            billing_status=AccountBillingStatusOptions.open.value,
        )
        self.item = self.make_charge_item()
        self.client.force_authenticate(user=self.user)

    def make_charge_item(self, account=None):
        return baker.make(
            ChargeItem,
            facility=self.facility,
            patient=self.patient,
            account=account or self.account,
            title="Consultation",
            status=ChargeItemStatusOptions.billable.value,
            quantity=Decimal("1.00"),
            unit_price_components=[
                {"amount": "100.00", "monetary_component_type": "base"}
            ],
            total_price_components=[
                {"amount": "100.00", "monetary_component_type": "base"}
            ],
            total_price=Decimal("100.00"),
        )

    def make_invoice(self, items=(), invoice_status=InvoiceStatusOptions.draft.value):
        invoice = baker.make(
            Invoice,
            facility=self.facility,
            account=self.account,
            patient=self.patient,
            status=invoice_status,
            charge_items=[item.id for item in items],
        )
        sync_invoice_items(invoice)
        invoice.save()
        return invoice

    def make_owned_invoice(self, invoice_status=InvoiceStatusOptions.draft.value):
        invoice = self.make_invoice([self.item], invoice_status=invoice_status)
        self.item.status = ChargeItemStatusOptions.billed.value
        self.item.paid_invoice = invoice
        self.item.save(update_fields=["status", "paid_invoice"])
        return invoice

    def invoice_url(self, action, invoice=None):
        kwargs = {"facility_external_id": self.facility.external_id}
        if invoice is not None:
            kwargs["external_id"] = invoice.external_id
        return reverse(f"invoice-{action}", kwargs=kwargs)

    def create_invoice(self, items):
        return self.client.post(
            self.invoice_url("list"),
            {
                "account": str(self.account.external_id),
                "status": InvoiceStatusOptions.draft.value,
                "number": "OWNERSHIP-TEST",
                "charge_items": [str(item.external_id) for item in items],
            },
            format="json",
        )

    def attach(self, invoice, items):
        return self.client.post(
            self.invoice_url("attach-items-to-invoice", invoice),
            {"charge_items": [str(item.external_id) for item in items]},
            format="json",
        )

    def assert_item_owned_by(self, invoice, item_status=ChargeItemStatusOptions.billed):
        self.item.refresh_from_db()
        invoice.refresh_from_db()
        self.assertEqual(self.item.paid_invoice_id, invoice.id)
        self.assertEqual(self.item.status, item_status.value)
        self.assertIn(self.item.id, invoice.charge_items)

    def invalid_requested_items(self):
        other_account = baker.make(
            Account,
            facility=self.facility,
            patient=self.patient,
            status=AccountStatusOptions.active.value,
            billing_status=AccountBillingStatusOptions.open.value,
        )
        return [
            ("nonexistent", ChargeItem(external_id=uuid4())),
            ("other_account", self.make_charge_item(account=other_account)),
        ]

    def test_create_rejects_any_unmatched_requested_item_without_claiming_items(self):
        invoice_count = Invoice.objects.count()
        for invalid_kind, invalid_item in self.invalid_requested_items():
            for include_valid_item in (False, True):
                with self.subTest(kind=invalid_kind, mixed=include_valid_item):
                    requested = [invalid_item]
                    if include_valid_item:
                        requested.append(self.item)

                    response = self.create_invoice(requested)

                    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                    self.assertEqual(Invoice.objects.count(), invoice_count)
                    self.item.refresh_from_db()
                    self.assertIsNone(self.item.paid_invoice_id)
                    self.assertEqual(self.item.status, ChargeItemStatusOptions.billable)

    def test_explicit_attach_rejects_any_unmatched_item_without_partial_attachment(
        self,
    ):
        target = self.make_owned_invoice()
        available = self.make_charge_item()
        for invalid_kind, invalid_item in self.invalid_requested_items():
            for include_valid_item in (False, True):
                with self.subTest(kind=invalid_kind, mixed=include_valid_item):
                    requested = [invalid_item]
                    if include_valid_item:
                        requested.append(available)

                    response = self.attach(target, requested)

                    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                    self.assert_item_owned_by(target)
                    self.assertEqual(target.charge_items, [self.item.id])
                    self.assertEqual(target.total_gross, Decimal("100.00"))
                    available.refresh_from_db()
                    self.assertIsNone(available.paid_invoice_id)
                    self.assertEqual(available.status, ChargeItemStatusOptions.billable)

    def test_create_accepts_duplicate_requested_ids_without_duplicate_billing(self):
        response = self.create_invoice([self.item, self.item])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invoice = Invoice.objects.get(external_id=response.data["id"])
        self.assert_item_owned_by(invoice)
        self.assertEqual(invoice.charge_items, [self.item.id])
        self.assertEqual(invoice.total_gross, Decimal("100.00"))

    def test_explicit_attach_accepts_duplicate_new_and_existing_ids(self):
        target = self.make_owned_invoice()
        available = self.make_charge_item()

        response = self.attach(target, [self.item, available, available, self.item])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assert_item_owned_by(target)
        available.refresh_from_db()
        self.assertEqual(available.paid_invoice_id, target.pk)
        self.assertEqual(available.status, ChargeItemStatusOptions.billed)
        self.assertCountEqual(target.charge_items, [self.item.id, available.id])
        self.assertEqual(target.total_gross, Decimal("200.00"))

    def test_create_rejects_item_already_on_a_draft_invoice(self):
        owner = self.make_owned_invoice()
        invoice_count = Invoice.objects.count()

        response = self.create_invoice([self.item])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Invoice.objects.count(), invoice_count)
        self.assert_item_owned_by(owner)

    def test_create_rejects_billable_item_with_an_existing_invoice_pointer(self):
        owner = self.make_owned_invoice()
        self.item.status = ChargeItemStatusOptions.billable.value
        self.item.save(update_fields=["status"])
        invoice_count = Invoice.objects.count()

        response = self.create_invoice([self.item])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Invoice.objects.count(), invoice_count)
        self.assert_item_owned_by(owner, ChargeItemStatusOptions.billable)

    def test_explicit_attach_rejects_item_already_on_a_draft_invoice(self):
        owner = self.make_owned_invoice()
        target = self.make_invoice()

        response = self.attach(target, [self.item])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        target.refresh_from_db()
        self.assertEqual(target.charge_items, [])
        self.assert_item_owned_by(owner)

    def test_explicit_attach_rejects_billable_item_with_an_existing_owner(self):
        owner = self.make_owned_invoice()
        self.item.status = ChargeItemStatusOptions.billable.value
        self.item.save(update_fields=["status"])
        target = self.make_invoice()
        available = self.make_charge_item()

        response = self.attach(target, [available, self.item])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        target.refresh_from_db()
        available.refresh_from_db()
        self.assertEqual(target.charge_items, [])
        self.assertIsNone(available.paid_invoice_id)
        self.assertEqual(available.status, ChargeItemStatusOptions.billable.value)
        self.assert_item_owned_by(owner, ChargeItemStatusOptions.billable)

    def test_account_attach_skips_items_billed_to_other_invoices(self):
        owner = self.make_owned_invoice()
        available = self.make_charge_item()
        target = self.make_invoice()

        response = self.client.post(
            self.invoice_url("attach-account-to-invoice", target)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        target.refresh_from_db()
        available.refresh_from_db()
        self.assertEqual(target.charge_items, [available.id])
        self.assertEqual(available.paid_invoice_id, target.id)
        self.assert_item_owned_by(owner)

    def test_account_attach_only_bills_items_selected_before_validation(self):
        target = self.make_invoice()
        original_validate = InvoiceViewSet.validate_items_for_attachment
        created_after_validation = []

        def create_charge_after_validation(view, charge_items, invoice=None):
            original_validate(view, charge_items, invoice)
            created_after_validation.append(self.make_charge_item())

        with patch.object(
            InvoiceViewSet,
            "validate_items_for_attachment",
            autospec=True,
            side_effect=create_charge_after_validation,
        ):
            response = self.client.post(
                self.invoice_url("attach-account-to-invoice", target)
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(created_after_validation), 1)
        later_item = created_after_validation[0]
        later_item.refresh_from_db()
        target.refresh_from_db()
        self.assertEqual(target.charge_items, [self.item.id])
        self.assertEqual(target.total_gross, Decimal("100.00"))
        self.assertEqual(later_item.status, ChargeItemStatusOptions.billable.value)
        self.assertIsNone(later_item.paid_invoice_id)
        self.assert_item_owned_by(target)

    def test_repeated_attachment_to_the_same_invoice_is_idempotent(self):
        target = self.make_invoice()

        response = self.attach(target, [self.item])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.attach(target, [self.item])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        target.refresh_from_db()
        self.assertEqual(target.charge_items, [self.item.id])
        self.assertEqual(target.total_gross, Decimal("100.00"))
        self.assert_item_owned_by(target)

    def test_account_attach_rejects_billable_item_still_owned_elsewhere(self):
        owner = self.make_owned_invoice()
        self.item.status = ChargeItemStatusOptions.billable.value
        self.item.save(update_fields=["status"])
        target = self.make_invoice()
        available = self.make_charge_item()

        response = self.client.post(
            self.invoice_url("attach-account-to-invoice", target)
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        target.refresh_from_db()
        available.refresh_from_db()
        self.assertEqual(target.charge_items, [])
        self.assertIsNone(available.paid_invoice_id)
        self.assert_item_owned_by(owner, ChargeItemStatusOptions.billable)

    def test_cannot_change_charge_item_status_while_attached_to_a_draft_invoice(self):
        owner = self.make_owned_invoice()
        url = reverse(
            "charge_item-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": self.item.external_id,
            },
        )

        for item_status in ChargeItemStatusOptions:
            if item_status == ChargeItemStatusOptions.billed:
                continue
            with self.subTest(status=item_status.value):
                response = self.client.put(
                    url,
                    {
                        "title": self.item.title,
                        "status": item_status.value,
                        "quantity": "1.00",
                        "unit_price_components": self.item.unit_price_components,
                    },
                    format="json",
                )

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assert_item_owned_by(owner)
                self.assertEqual(owner.charge_items, [self.item.id])
                self.assertEqual(owner.status, InvoiceStatusOptions.draft.value)

    def test_charge_item_can_be_aborted_after_invoice_action_removes_it(self):
        owner = self.make_owned_invoice()

        response = self.client.post(
            self.invoice_url("remove-item-from-invoice", owner),
            {"charge_item": str(self.item.external_id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.item.refresh_from_db()
        self.assertIsNone(self.item.paid_invoice_id)

        response = self.client.put(
            reverse(
                "charge_item-detail",
                kwargs={
                    "facility_external_id": self.facility.external_id,
                    "external_id": self.item.external_id,
                },
            ),
            {
                "title": self.item.title,
                "status": ChargeItemStatusOptions.aborted.value,
                "quantity": "1.00",
                "unit_price_components": self.item.unit_price_components,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.item.refresh_from_db()
        owner.refresh_from_db()
        self.assertEqual(self.item.status, ChargeItemStatusOptions.aborted.value)
        self.assertIsNone(self.item.paid_invoice_id)
        self.assertEqual(owner.charge_items, [])
        self.assertEqual(owner.status, InvoiceStatusOptions.draft.value)

    def test_billed_charge_item_can_be_edited_while_its_invoice_is_a_draft(self):
        owner = self.make_owned_invoice()

        response = self.client.put(
            reverse(
                "charge_item-detail",
                kwargs={
                    "facility_external_id": self.facility.external_id,
                    "external_id": self.item.external_id,
                },
            ),
            {
                "title": "Updated consultation",
                "quantity": "2.00",
                "unit_price_components": self.item.unit_price_components,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assert_item_owned_by(owner)
        self.assertEqual(self.item.title, "Updated consultation")
        self.assertEqual(self.item.quantity, Decimal("2.00"))
        self.assertEqual(self.item.total_price, Decimal("200.00"))
        self.assertEqual(owner.status, InvoiceStatusOptions.draft.value)
        self.assertEqual(owner.charge_items, [self.item.id])
        self.assertEqual(owner.total_gross, Decimal("200.00"))

    def test_frontend_upsert_can_edit_billed_draft_items_and_recalculate_invoice(self):
        owner = self.make_owned_invoice()
        second_item = self.make_charge_item()
        response = self.attach(owner, [second_item])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post(
            reverse(
                "charge_item-upsert",
                kwargs={"facility_external_id": self.facility.external_id},
            ),
            {
                "datapoints": [
                    {
                        "id": str(item.external_id),
                        "title": "Edited invoice item",
                        "status": ChargeItemStatusOptions.billed.value,
                        "quantity": quantity,
                        "unit_price_components": [
                            {"amount": amount, "monetary_component_type": "base"}
                        ],
                    }
                    for item, quantity, amount in [
                        (self.item, "2.00", "150.00"),
                        (second_item, "3.00", "50.00"),
                    ]
                ]
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assert_item_owned_by(owner)
        second_item.refresh_from_db()
        self.assertEqual(second_item.paid_invoice_id, owner.pk)
        self.assertEqual(second_item.status, ChargeItemStatusOptions.billed.value)
        self.assertEqual(self.item.total_price, Decimal("300.00"))
        self.assertEqual(second_item.total_price, Decimal("150.00"))
        self.assertCountEqual(owner.charge_items, [self.item.pk, second_item.pk])
        self.assertEqual(owner.total_gross, Decimal("450.00"))
        self.assertEqual(owner.status, InvoiceStatusOptions.draft.value)
        self.assertEqual(Invoice.objects.count(), 1)

    def test_unchanged_managed_status_does_not_allow_editing_finalized_invoice_items(
        self,
    ):
        owner = self.make_owned_invoice()
        for invoice_status, item_status in [
            (InvoiceStatusOptions.issued, ChargeItemStatusOptions.billed),
            (InvoiceStatusOptions.balanced, ChargeItemStatusOptions.paid),
        ]:
            with self.subTest(invoice_status=invoice_status.value):
                response = self.client.put(
                    self.invoice_url("detail", owner),
                    {"status": invoice_status.value},
                    format="json",
                )
                self.assertEqual(response.status_code, status.HTTP_200_OK)

                response = self.client.put(
                    reverse(
                        "charge_item-detail",
                        kwargs={
                            "facility_external_id": self.facility.external_id,
                            "external_id": self.item.external_id,
                        },
                    ),
                    {
                        "title": "Forbidden edit",
                        "status": item_status.value,
                        "quantity": "2.00",
                        "unit_price_components": self.item.unit_price_components,
                    },
                    format="json",
                )

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assert_item_owned_by(owner, item_status)
                self.assertEqual(self.item.title, "Consultation")
                self.assertEqual(self.item.quantity, Decimal("1.00"))
                self.assertEqual(owner.total_gross, Decimal("100.00"))
                self.assertEqual(owner.status, invoice_status.value)

    def test_cannot_balance_invoice_when_charge_item_points_to_another_invoice(self):
        owner = self.make_owned_invoice(
            invoice_status=InvoiceStatusOptions.issued.value
        )
        other = self.make_invoice(invoice_status=InvoiceStatusOptions.issued.value)
        self.item.paid_invoice = other
        self.item.save(update_fields=["paid_invoice"])

        response = self.client.put(
            self.invoice_url("detail", owner),
            {"status": InvoiceStatusOptions.balanced.value},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        owner.refresh_from_db()
        self.item.refresh_from_db()
        self.assertEqual(owner.status, InvoiceStatusOptions.issued.value)
        self.assertEqual(self.item.paid_invoice_id, other.id)
        self.assertEqual(self.item.status, ChargeItemStatusOptions.billed.value)
        self.assertIsNone(self.item.paid_on)

    def test_cannot_issue_invoice_when_charge_item_points_to_another_invoice(self):
        owner = self.make_owned_invoice()
        other = self.make_invoice()
        self.item.paid_invoice = other
        self.item.save(update_fields=["paid_invoice"])

        response = self.client.put(
            self.invoice_url("detail", owner),
            {"status": InvoiceStatusOptions.issued.value},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        owner.refresh_from_db()
        self.item.refresh_from_db()
        self.assertEqual(owner.status, InvoiceStatusOptions.draft.value)
        self.assertEqual(self.item.paid_invoice_id, other.id)

    def test_unshared_invoice_can_be_issued_then_balanced(self):
        owner = self.make_owned_invoice()

        response = self.client.put(
            self.invoice_url("detail", owner),
            {"status": InvoiceStatusOptions.issued.value},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        owner.refresh_from_db()
        self.assertEqual(owner.status, InvoiceStatusOptions.issued.value)

        response = self.client.put(
            self.invoice_url("detail", owner),
            {"status": InvoiceStatusOptions.balanced.value},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        owner.refresh_from_db()
        self.assertEqual(owner.status, InvoiceStatusOptions.balanced.value)
        self.assert_item_owned_by(owner, ChargeItemStatusOptions.paid)
        self.assertIsNotNone(self.item.paid_on)

    def test_cancelled_invoice_keeps_history_and_allows_rebilling(self):
        owner = self.make_owned_invoice(
            invoice_status=InvoiceStatusOptions.issued.value
        )

        response = self.client.post(
            self.invoice_url("cancel-invoice", owner),
            {"reason": InvoiceStatusOptions.cancelled.value},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        owner.refresh_from_db()
        self.item.refresh_from_db()
        self.assertEqual(owner.status, InvoiceStatusOptions.cancelled.value)
        self.assertIn(self.item.id, owner.charge_items)
        self.assertEqual(self.item.status, ChargeItemStatusOptions.billable.value)
        self.assertIsNone(self.item.paid_invoice_id)

        response = self.create_invoice([self.item])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        replacement = Invoice.objects.get(external_id=response.data["id"])
        self.assert_item_owned_by(replacement)
        owner.refresh_from_db()
        self.assertIn(self.item.id, owner.charge_items)

    def test_removing_a_charge_item_allows_attachment_to_another_invoice(self):
        owner = self.make_owned_invoice()
        target = self.make_invoice()

        response = self.client.post(
            self.invoice_url("remove-item-from-invoice", owner),
            {"charge_item": str(self.item.external_id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        owner.refresh_from_db()
        self.item.refresh_from_db()
        self.assertEqual(owner.charge_items, [])
        self.assertIsNone(self.item.paid_invoice_id)

        response = self.attach(target, [self.item])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assert_item_owned_by(target)

    def test_remove_cannot_release_a_charge_item_owned_by_another_invoice(self):
        owner = self.make_owned_invoice()
        duplicate = self.make_invoice([self.item])

        response = self.client.post(
            self.invoice_url("remove-item-from-invoice", duplicate),
            {"charge_item": str(self.item.external_id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assert_item_owned_by(owner)

    def test_cancelling_shared_invoice_does_not_release_the_other_owners_item(self):
        owner = self.make_owned_invoice()
        duplicate = self.make_invoice([self.item])

        response = self.client.post(
            self.invoice_url("cancel-invoice", duplicate),
            {"reason": InvoiceStatusOptions.cancelled.value},
            format="json",
        )

        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST],
        )
        self.assert_item_owned_by(owner)

    def test_change_account_rejects_billable_item_still_owned_elsewhere(self):
        owner = self.make_owned_invoice()
        self.item.status = ChargeItemStatusOptions.billable.value
        self.item.save(update_fields=["status"])
        target_account = baker.make(
            Account,
            facility=self.facility,
            patient=self.patient,
            status=AccountStatusOptions.active.value,
            billing_status=AccountBillingStatusOptions.open.value,
        )

        response = self.client.post(
            reverse(
                "charge_item-change-account",
                kwargs={"facility_external_id": self.facility.external_id},
            ),
            {
                "charge_items": [str(self.item.external_id)],
                "target_account": str(target_account.external_id),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assert_item_owned_by(owner, ChargeItemStatusOptions.billable)
        self.assertEqual(self.item.account_id, self.account.id)

    def test_cancellation_helper_reloads_stale_item_before_checking_invoice(self):
        stale_item = ChargeItem.objects.get(id=self.item.id)
        owner = self.make_owned_invoice(
            invoice_status=InvoiceStatusOptions.issued.value
        )

        with self.assertRaises(ValidationError):
            handle_charge_item_cancel(stale_item)

        self.assert_item_owned_by(owner)
        owner.refresh_from_db()
        self.assertEqual(owner.status, InvoiceStatusOptions.issued.value)
