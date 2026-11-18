from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from unittest.mock import patch

from django.db import close_old_connections, connections
from django.test import TransactionTestCase, override_settings, skipUnlessDBFeature
from django.urls import reverse
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from care.emr.api.viewsets.base import EMRUpdateMixin
from care.emr.locks.billing import AccountLock
from care.emr.models.account import Account
from care.emr.models.charge_item import ChargeItem
from care.emr.models.invoice import Invoice
from care.emr.resources.invoice.sync_items import sync_invoice_items


@override_settings(DEBUG_PROPAGATE_EXCEPTIONS=True)
@skipUnlessDBFeature("has_select_for_update_nowait", "has_select_for_no_key_update")
class UpsertTransactionTests(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        database_settings = connections["default"].settings_dict
        original_atomic_requests = database_settings["ATOMIC_REQUESTS"]
        database_settings["ATOMIC_REQUESTS"] = True
        cls.addClassCleanup(
            database_settings.__setitem__, "ATOMIC_REQUESTS", original_atomic_requests
        )

    def setUp(self):
        self.user = baker.make("users.User", is_superuser=True)
        self.facility = baker.make("facility.Facility", created_by=self.user)
        self.patient = baker.make("emr.Patient")
        self.accounts = [
            baker.make(
                Account,
                facility=self.facility,
                patient=self.patient,
                status="active",
                billing_status="open",
            )
            for _ in range(2)
        ]
        self.items = [self.make_item(account) for account in self.accounts]
        self.url = reverse(
            "charge_item-upsert",
            kwargs={"facility_external_id": self.facility.external_id},
        )

    def make_item(self, account):
        item = baker.make(
            ChargeItem,
            facility=self.facility,
            patient=self.patient,
            account=account,
            title="Original consultation",
            status="billed",
            quantity=Decimal("1.00"),
            unit_price_components=[
                {"amount": "100.00", "monetary_component_type": "base"}
            ],
            total_price_components=[
                {"amount": "100.00", "monetary_component_type": "base"}
            ],
            total_price=Decimal("100.00"),
        )
        invoice = baker.make(
            Invoice,
            facility=self.facility,
            patient=self.patient,
            account=account,
            status="draft",
            charge_items=[item.pk],
        )
        item.paid_invoice = invoice
        item.save(update_fields=["paid_invoice"])
        sync_invoice_items(invoice)
        invoice.save()
        return item

    def in_another_connection(self, operation):
        close_old_connections()
        try:
            return operation()
        finally:
            connections["default"].close()

    def upsert(self, items):
        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.post(
            self.url,
            {
                "datapoints": [
                    {
                        "id": str(item.external_id),
                        "title": "Updated consultation",
                        "status": "billed",
                        "quantity": "2.00",
                        "unit_price_components": [
                            {"amount": "150.00", "monetary_component_type": "base"}
                        ],
                    }
                    for item in items
                ]
            },
            format="json",
        )
        return response.status_code, response.data

    def assert_items_unchanged(self, items):
        for item in items:
            invoice_id = item.paid_invoice_id
            item.refresh_from_db()
            self.assertEqual(item.title, "Original consultation")
            self.assertEqual(item.quantity, Decimal("1.00"))
            self.assertEqual(item.total_price, Decimal("100.00"))
            self.assertEqual(item.status, "billed")
            self.assertEqual(item.paid_invoice_id, invoice_id)
            invoice = Invoice.objects.get(pk=invoice_id)
            self.assertEqual(invoice.charge_items, [item.pk])
            self.assertEqual(invoice.total_gross, Decimal("100.00"))

    def test_locked_first_item_does_not_break_second_item_lookup(self):
        items = [self.items[0], self.make_item(self.accounts[0])]
        with (
            ThreadPoolExecutor(max_workers=1) as executor,
            AccountLock(self.accounts[0]),
        ):
            future = executor.submit(
                self.in_another_connection, lambda: self.upsert(items)
            )
            response_status, data = future.result(timeout=15)

        self.assertEqual(response_status, status.HTTP_400_BAD_REQUEST, data)
        self.assertEqual(len(data), 2)
        for result in data:
            self.assertIn("locked", str(result["detail"]))
        self.assert_items_unchanged(items)

    def test_lock_failure_rolls_back_successful_items_in_either_order(self):
        locked, unlocked = self.items
        for items in ([locked, unlocked], [unlocked, locked]):
            with self.subTest(first_item_locked=items[0] == locked):
                with (
                    ThreadPoolExecutor(max_workers=1) as executor,
                    AccountLock(self.accounts[0]),
                ):
                    future = executor.submit(
                        self.in_another_connection,
                        lambda items=items: self.upsert(items),
                    )
                    response_status, data = future.result(timeout=15)

                self.assertEqual(response_status, status.HTTP_400_BAD_REQUEST, data)
                self.assertEqual(len(data), 2)
                self.assertIn("locked", str(data[items.index(locked)]["detail"]))
                self.assertEqual(
                    data[items.index(unlocked)]["id"], str(unlocked.external_id)
                )
                self.assert_items_unchanged(items)

    def test_successful_batch_commits_item_and_invoice_changes(self):
        response_status, data = self.upsert(self.items)

        self.assertEqual(response_status, status.HTTP_200_OK, data)
        self.assertEqual(len(data), 2)
        for item in self.items:
            item.refresh_from_db()
            self.assertEqual(item.title, "Updated consultation")
            self.assertEqual(item.quantity, Decimal("2.00"))
            self.assertEqual(item.total_price, Decimal("300.00"))
            self.assertEqual(item.status, "billed")
            self.assertEqual(item.paid_invoice.total_gross, Decimal("300.00"))
            self.assertEqual(item.paid_invoice.charge_items, [item.pk])

    def test_unhandled_failure_is_raised_and_rolls_back_entire_batch(self):
        perform_update = EMRUpdateMixin.perform_update

        def fail_after_second_save(view, instance):
            perform_update(view, instance)
            if instance.pk == self.items[1].pk:
                raise ValueError("Unexpected update failure")

        with (
            patch.object(EMRUpdateMixin, "perform_update", fail_after_second_save),
            self.assertRaisesMessage(ValueError, "Unexpected update failure"),
        ):
            self.upsert(self.items)

        self.assert_items_unchanged(self.items)
