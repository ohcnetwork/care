from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Event
from unittest.mock import patch

from django.db import close_old_connections, connections, transaction
from django.test import TransactionTestCase, skipUnlessDBFeature
from django.urls import reverse
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from care.emr.api.viewsets.account import AccountViewSet
from care.emr.locks.billing import AccountLock
from care.emr.models.account import Account
from care.emr.models.charge_item import ChargeItem
from care.emr.models.invoice import Invoice
from care.emr.resources.account.sync_items import (
    rebalance_account_task,
    sync_account_items,
)
from care.utils.lock import ObjectLocked


@skipUnlessDBFeature("has_select_for_update_nowait", "has_select_for_no_key_update")
class AccountBillingUpdateTests(TransactionTestCase):
    def setUp(self):
        self.user = baker.make("users.User", is_superuser=True)
        self.facility = baker.make("facility.Facility", created_by=self.user)
        self.patient = baker.make("emr.Patient")
        self.account = baker.make(
            Account,
            facility=self.facility,
            patient=self.patient,
            name="Original account",
            status="active",
            billing_status="open",
            total_gross=0,
            total_balance=0,
        )
        self.item = baker.make(
            ChargeItem,
            facility=self.facility,
            patient=self.patient,
            account=self.account,
            status="billable",
            quantity=Decimal("1.00"),
            total_price=Decimal("100.00"),
            unit_price_components=[
                {"amount": "100.00", "monetary_component_type": "base"}
            ],
            total_price_components=[
                {"amount": "100.00", "monetary_component_type": "base"}
            ],
        )

    def in_another_connection(self, operation):
        close_old_connections()
        try:
            return operation()
        finally:
            connections["default"].close()

    def request(self, method, url, data):
        client = APIClient()
        client.force_authenticate(user=self.user)
        response = getattr(client, method)(url, data, format="json")
        return response.status_code, response.data

    def account_url(self, action):
        return reverse(
            f"account-{action}",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": self.account.external_id,
            },
        )

    def update_metadata(self):
        return self.request(
            "put",
            self.account_url("detail"),
            {
                "name": "Renamed account",
                "status": "active",
                "billing_status": "open",
                "service_period": {},
            },
        )

    def create_invoice(self):
        return self.request(
            "post",
            reverse(
                "invoice-list",
                kwargs={"facility_external_id": self.facility.external_id},
            ),
            {
                "account": str(self.account.external_id),
                "status": "draft",
                "number": "ACCOUNT-METADATA-RACE",
                "charge_items": [str(self.item.external_id)],
            },
        )

    def read_locked_account(self):
        account = Account.objects.get(pk=self.account.pk)
        with AccountLock(account):
            account.refresh_from_db()
            return account.name, account.total_gross

    def test_stale_metadata_update_keeps_committed_invoice_totals(self):
        loaded = Event()
        resume = Event()
        get_object = AccountViewSet.get_object

        def pause_after_read(view):
            account = get_object(view)
            self.assertEqual(account.total_gross, Decimal(0))
            loaded.set()
            self.assertTrue(resume.wait(timeout=10))
            return account

        with (
            ThreadPoolExecutor(max_workers=1) as executor,
            patch.object(AccountViewSet, "get_object", pause_after_read),
        ):
            future = executor.submit(self.in_another_connection, self.update_metadata)
            try:
                self.assertTrue(loaded.wait(timeout=5))
                response_status, invoice_data = self.create_invoice()
                self.assertEqual(response_status, status.HTTP_200_OK)
                self.account.refresh_from_db()
                self.assertEqual(self.account.total_gross, Decimal("100.00"))
            finally:
                resume.set()
            response_status, _ = future.result(timeout=10)
            self.assertEqual(response_status, status.HTTP_200_OK)

        self.account.refresh_from_db()
        invoice = Invoice.objects.get(external_id=invoice_data["id"])
        self.assertEqual(self.account.name, "Renamed account")
        self.assertEqual(invoice.total_gross, Decimal("100.00"))
        self.assertEqual(self.account.total_gross, invoice.total_gross)
        self.assertEqual(self.account.total_balance, invoice.total_gross)

    def test_account_actions_conflict_until_billing_transaction_commits(self):
        operations = [
            self.update_metadata,
            lambda: self.request("post", self.account_url("rebalance"), {}),
        ]
        with ThreadPoolExecutor(max_workers=1) as executor:
            for operation in operations:
                with transaction.atomic():
                    with AccountLock(self.account):
                        pass
                    future = executor.submit(self.in_another_connection, operation)
                    response_status, _ = future.result(timeout=10)
                    self.assertEqual(response_status, status.HTTP_423_LOCKED)
                future = executor.submit(self.in_another_connection, operation)
                response_status, _ = future.result(timeout=10)
                self.assertEqual(response_status, status.HTTP_200_OK)

    def test_background_rebalance_keeps_compute_and_save_in_one_lock(self):
        response_status, _ = self.create_invoice()
        self.assertEqual(response_status, status.HTTP_200_OK)

        with ThreadPoolExecutor(max_workers=1) as executor:

            def compute_then_check_lock(account):
                sync_account_items(account)
                future = executor.submit(
                    self.in_another_connection, self.read_locked_account
                )
                with self.assertRaises(ObjectLocked):
                    future.result(timeout=5)

            with patch(
                "care.emr.resources.account.sync_items.sync_account_items",
                side_effect=compute_then_check_lock,
            ):
                rebalance_account_task(self.account.pk)

            future = executor.submit(
                self.in_another_connection, self.read_locked_account
            )
            self.assertEqual(
                future.result(timeout=5), ("Original account", Decimal("100.00"))
            )

    def test_background_rebalance_refreshes_metadata_before_saving(self):
        stale_account = Account.objects.get(pk=self.account.pk)
        response_status, _ = self.update_metadata()
        self.assertEqual(response_status, status.HTTP_200_OK)

        with patch.object(Account.objects, "get", return_value=stale_account):
            rebalance_account_task(self.account.pk)

        self.account.refresh_from_db()
        self.assertEqual(self.account.name, "Renamed account")
