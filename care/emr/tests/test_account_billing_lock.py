from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Event
from unittest.mock import patch
from uuid import uuid4

from django.db import close_old_connections, connections, transaction
from django.test import TransactionTestCase, skipUnlessDBFeature
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from model_bakery import baker
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from care.emr.api.viewsets.charge_item import ChargeItemViewSet
from care.emr.locks.billing import AccountLock
from care.emr.models.account import Account
from care.emr.models.charge_item import ChargeItem
from care.emr.models.invoice import Invoice
from care.emr.resources.charge_item.handle_charge_item_cancel import (
    handle_charge_item_cancel,
)
from care.emr.resources.invoice.sync_items import sync_invoice_items
from care.utils.lock import ObjectLocked


@skipUnlessDBFeature("has_select_for_update_nowait", "has_select_for_no_key_update")
class AccountBillingLockTests(TransactionTestCase):
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
        )
        self.item = baker.make(
            ChargeItem,
            facility=self.facility,
            patient=self.patient,
            account=self.account,
            title="Consultation",
            status="billable",
            quantity=Decimal("1.00"),
            unit_price_components=[
                {"amount": "100.00", "monetary_component_type": "base"}
            ],
            total_price_components=[
                {"amount": "100.00", "monetary_component_type": "base"}
            ],
            total_price=Decimal("100.00"),
        )

    def in_another_connection(self, operation):
        close_old_connections()
        try:
            return operation()
        finally:
            connections["default"].close()

    def read_locked_account(self):
        account = Account.objects.get(pk=self.account.pk)
        with AccountLock(account):
            account.refresh_from_db()
            return account.name

    def make_account(self):
        return baker.make(
            Account,
            facility=self.facility,
            patient=self.patient,
            status="active",
            billing_status="open",
        )

    def make_charge_item(self, account):
        return baker.make(
            ChargeItem,
            facility=account.facility,
            patient=account.patient,
            account=account,
            status="billable",
            quantity=Decimal("1.00"),
            total_price=Decimal("100.00"),
            unit_price_components=[],
            total_price_components=[],
        )

    def change_account(self, items, target):
        return self.request(
            "post",
            reverse(
                "charge_item-change-account",
                kwargs={"facility_external_id": self.facility.external_id},
            ),
            {
                "charge_items": [str(item.external_id) for item in items],
                "target_account": str(target.external_id),
            },
        )

    def invoice_url(self, action, invoice=None):
        kwargs = {"facility_external_id": self.facility.external_id}
        if invoice is not None:
            kwargs["external_id"] = invoice.external_id
        return reverse(f"invoice-{action}", kwargs=kwargs)

    def request(self, method, url, data):
        client = APIClient()
        client.force_authenticate(user=self.user)
        response = getattr(client, method)(url, data, format="json")
        return response.status_code, response.data

    def create_invoice(self):
        return self.request(
            "post",
            self.invoice_url("list"),
            {
                "account": str(self.account.external_id),
                "status": "draft",
                "number": "DATABASE-LOCK-TEST",
                "charge_items": [str(self.item.external_id)],
            },
        )

    def make_invoice(self, *, owns_item=False, invoice_status="draft"):
        invoice = baker.make(
            Invoice,
            facility=self.facility,
            patient=self.patient,
            account=self.account,
            status=invoice_status,
            charge_items=[self.item.pk] if owns_item else [],
        )
        if owns_item:
            self.item.status = "billed"
            self.item.paid_invoice = invoice
            self.item.save(update_fields=["status", "paid_invoice"])
        sync_invoice_items(invoice)
        invoice.save()
        return invoice

    def assert_request_conflicts_until_commit(self, operation):
        with ThreadPoolExecutor(max_workers=1) as executor:
            with transaction.atomic():
                with AccountLock(self.account):
                    pass
                # The lock's Python scope has ended; the transaction is open.
                future = executor.submit(self.in_another_connection, operation)
                response_status, _ = future.result(timeout=10)
                self.assertEqual(response_status, status.HTTP_423_LOCKED)
            future = executor.submit(self.in_another_connection, operation)
            response_status, data = future.result(timeout=10)
            self.assertEqual(response_status, status.HTTP_200_OK)
        return data

    def test_lock_survives_its_context_until_outer_commit(self):
        with ThreadPoolExecutor(max_workers=1) as executor:
            with transaction.atomic():
                with AccountLock(self.account):
                    Account.objects.filter(pk=self.account.pk).update(name="Updated")
                future = executor.submit(
                    self.in_another_connection, self.read_locked_account
                )
                with self.assertRaises(ObjectLocked):
                    future.result(timeout=5)
            future = executor.submit(
                self.in_another_connection, self.read_locked_account
            )
            self.assertEqual(future.result(timeout=5), "Updated")

    def test_outer_rollback_releases_lock_and_discards_changes(self):
        with ThreadPoolExecutor(max_workers=1) as executor:
            with self.assertRaisesMessage(ValueError, "rollback"), transaction.atomic():
                with AccountLock(self.account):
                    Account.objects.filter(pk=self.account.pk).update(name="Discarded")
                future = executor.submit(
                    self.in_another_connection, self.read_locked_account
                )
                with self.assertRaises(ObjectLocked):
                    future.result(timeout=5)
                raise ValueError("rollback")
            future = executor.submit(
                self.in_another_connection, self.read_locked_account
            )
            self.assertEqual(future.result(timeout=5), "Original account")

    def test_rejected_acquisition_leaves_contenders_transaction_usable(self):
        def contend_then_read():
            account = Account.objects.get(pk=self.account.pk)
            with transaction.atomic():
                with self.assertRaises(ObjectLocked), AccountLock(account):
                    self.fail("A second connection must not acquire this account")
                return Account.objects.get(pk=self.account.pk).name

        with ThreadPoolExecutor(max_workers=1) as executor, AccountLock(self.account):
            future = executor.submit(self.in_another_connection, contend_then_read)
            self.assertEqual(future.result(timeout=5), "Original account")

    def test_repeated_locks_are_reentrant_within_one_transaction(self):
        lock = AccountLock(self.account)
        with transaction.atomic(), lock:
            Account.objects.filter(pk=self.account.pk).update(name="Updated")
            with lock, AccountLock(self.account):
                self.assertEqual(
                    Account.objects.get(pk=self.account.pk).name, "Updated"
                )

    def test_account_list_locks_all_unique_rows_until_outer_commit(self):
        second = self.make_account()

        def lock_account(account):
            with AccountLock(account):
                return account.pk

        with ThreadPoolExecutor(max_workers=1) as executor:
            with transaction.atomic():
                with AccountLock([second, self.account, second, self.account]):
                    pass
                for account in [self.account, second]:
                    future = executor.submit(
                        self.in_another_connection,
                        lambda account=account: lock_account(account),
                    )
                    with self.assertRaises(ObjectLocked):
                        future.result(timeout=5)
            for account in [self.account, second]:
                future = executor.submit(
                    self.in_another_connection,
                    lambda account=account: lock_account(account),
                )
                self.assertEqual(future.result(timeout=5), account.pk)

    def test_failed_account_list_releases_rows_acquired_before_conflict(self):
        second = self.make_account()
        failed = Event()
        release = Event()

        def contend():
            with transaction.atomic():
                with (
                    self.assertRaises(ObjectLocked),
                    AccountLock([second, self.account]),
                ):
                    self.fail("The locked second account must reject the batch")
                failed.set()
                self.assertTrue(release.wait(timeout=10))

        with ThreadPoolExecutor(max_workers=1) as executor, AccountLock(second):
            future = executor.submit(self.in_another_connection, contend)
            try:
                self.assertTrue(failed.wait(timeout=5))
                # The contender's outer transaction remains open, but its failed
                # acquisition must have released the first row with its savepoint.
                with AccountLock(self.account):
                    pass
            finally:
                release.set()
                future.result(timeout=5)

    def test_change_account_moves_items_from_unique_sources_with_repeated_ids(self):
        second_source = self.make_account()
        target = self.make_account()
        second_item = self.make_charge_item(second_source)

        response_status, _ = self.change_account(
            [self.item, second_item, self.item], target
        )

        self.assertEqual(response_status, status.HTTP_201_CREATED)
        for item in [self.item, second_item]:
            item.refresh_from_db()
            self.assertEqual(item.account_id, target.pk)
            self.assertEqual(item.status, "billable")
            self.assertIsNone(item.paid_invoice_id)

        # A source may also be the destination without acquiring it twice.
        response_status, _ = self.change_account([self.item, second_item], target)
        self.assertEqual(response_status, status.HTTP_201_CREATED)

    def assert_change_account_rolls_back_earlier_item(self, rejected_item, target):
        manager = ChargeItem.objects
        get_queryset = manager.get_queryset
        with (
            patch.object(
                manager,
                "get_queryset",
                side_effect=lambda: get_queryset().order_by("pk"),
            ),
            CaptureQueriesContext(connections["default"]) as queries,
        ):
            response_status, _ = self.change_account([self.item, rejected_item], target)

        self.assertEqual(response_status, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(
            any(
                query["sql"].startswith('UPDATE "emr_chargeitem" ') for query in queries
            ),
            "The earlier valid item must be updated before the later rejection",
        )
        self.item.refresh_from_db()
        rejected_item.refresh_from_db()
        self.assertEqual(self.item.account_id, self.account.pk)
        self.assertEqual(rejected_item.account_id, self.account.pk)

    def test_change_account_rolls_back_when_a_later_item_is_not_billable(self):
        rejected_item = self.make_charge_item(self.account)
        rejected_item.status = "aborted"
        rejected_item.save(update_fields=["status"])

        self.assert_change_account_rolls_back_earlier_item(
            rejected_item, self.make_account()
        )

        self.assertEqual(rejected_item.status, "aborted")

    def test_change_account_rolls_back_when_a_later_item_has_an_invoice(self):
        rejected_item = self.make_charge_item(self.account)
        owner = self.make_invoice()
        rejected_item.paid_invoice = owner
        rejected_item.save(update_fields=["paid_invoice"])

        self.assert_change_account_rolls_back_earlier_item(
            rejected_item, self.make_account()
        )

        self.assertEqual(rejected_item.paid_invoice_id, owner.pk)

    def test_change_account_reads_requested_items_in_bulk(self):
        target = self.make_account()
        items = [self.item, *[self.make_charge_item(self.account) for _ in range(2)]]

        with CaptureQueriesContext(connections["default"]) as queries:
            response_status, _ = self.change_account(items, target)

        self.assertEqual(response_status, status.HTTP_201_CREATED)
        item_reads = [
            query["sql"]
            for query in queries
            if query["sql"].startswith('SELECT "emr_chargeitem".')
        ]
        # Read the batch before locking and refresh it together after locking.
        self.assertLessEqual(len(item_reads), 2)

    def test_change_account_rejects_a_missing_item_without_partial_moves(self):
        target = self.make_account()

        response_status, _ = self.request(
            "post",
            reverse(
                "charge_item-change-account",
                kwargs={"facility_external_id": self.facility.external_id},
            ),
            {
                "charge_items": [str(self.item.external_id), str(uuid4())],
                "target_account": str(target.external_id),
            },
        )

        self.assertEqual(response_status, status.HTTP_404_NOT_FOUND)
        self.item.refresh_from_db()
        self.assertEqual(self.item.account_id, self.account.pk)

    def test_change_account_rejects_another_patients_item_without_partial_moves(self):
        other_patient = baker.make("emr.Patient")
        other_account = baker.make(
            Account,
            facility=self.facility,
            patient=other_patient,
            status="active",
            billing_status="open",
        )
        other_item = self.make_charge_item(other_account)
        target = self.make_account()

        response_status, _ = self.change_account([self.item, other_item], target)

        self.assertEqual(response_status, status.HTTP_404_NOT_FOUND)
        self.item.refresh_from_db()
        other_item.refresh_from_db()
        self.assertEqual(self.item.account_id, self.account.pk)
        self.assertEqual(other_item.account_id, other_account.pk)

    def test_change_account_rejects_another_facilitys_item_without_partial_moves(self):
        other_facility = baker.make("facility.Facility", created_by=self.user)
        other_account = baker.make(
            Account,
            facility=other_facility,
            patient=self.patient,
            status="active",
            billing_status="open",
        )
        other_item = self.make_charge_item(other_account)
        target = self.make_account()

        response_status, _ = self.change_account([self.item, other_item], target)

        self.assertEqual(response_status, status.HTTP_404_NOT_FOUND)
        self.item.refresh_from_db()
        other_item.refresh_from_db()
        self.assertEqual(self.item.account_id, self.account.pk)
        self.assertEqual(other_item.account_id, other_account.pk)

    def test_change_account_conflicts_on_any_source_or_destination_without_partial_moves(
        self,
    ):
        second_source = self.make_account()
        target = self.make_account()
        second_item = self.make_charge_item(second_source)

        def move():
            return self.change_account([self.item, second_item], target)

        with ThreadPoolExecutor(max_workers=1) as executor:
            for locked_account in [second_source, target]:
                with (
                    self.subTest(locked_account=locked_account.pk),
                    transaction.atomic(),
                ):
                    with AccountLock(locked_account):
                        pass
                    future = executor.submit(self.in_another_connection, move)
                    response_status, _ = future.result(timeout=10)
                    self.assertEqual(response_status, status.HTTP_423_LOCKED)
                    self.item.refresh_from_db()
                    second_item.refresh_from_db()
                    self.assertEqual(self.item.account_id, self.account.pk)
                    self.assertEqual(second_item.account_id, second_source.pk)
            future = executor.submit(self.in_another_connection, move)
            response_status, _ = future.result(timeout=10)
            self.assertEqual(response_status, status.HTTP_201_CREATED)
        self.item.refresh_from_db()
        second_item.refresh_from_db()
        self.assertEqual(self.item.account_id, target.pk)
        self.assertEqual(second_item.account_id, target.pk)

    def test_error_in_lock_rolls_back_changes_and_allows_retry(self):
        with (
            self.assertRaisesMessage(ValueError, "rollback"),
            AccountLock(self.account),
        ):
            Account.objects.filter(pk=self.account.pk).update(name="Discarded")
            raise ValueError("rollback")
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                self.in_another_connection, self.read_locked_account
            )
            self.assertEqual(future.result(timeout=5), "Original account")

    def test_creation_conflicts_until_account_transaction_commits(self):
        data = self.assert_request_conflicts_until_commit(self.create_invoice)
        invoice = Invoice.objects.get(external_id=data["id"])
        self.item.refresh_from_db()
        self.assertEqual(Invoice.objects.count(), 1)
        self.assertEqual(invoice.charge_items, [self.item.pk])
        self.assertEqual(self.item.paid_invoice_id, invoice.pk)
        self.assertEqual(self.item.status, "billed")

    def test_attachment_conflicts_until_account_transaction_commits(self):
        invoice = self.make_invoice()

        def attach():
            return self.request(
                "post",
                self.invoice_url("attach-items-to-invoice", invoice),
                {"charge_items": [str(self.item.external_id)]},
            )

        self.assert_request_conflicts_until_commit(attach)
        invoice.refresh_from_db()
        self.item.refresh_from_db()
        self.assertEqual(invoice.charge_items, [self.item.pk])
        self.assertEqual(self.item.paid_invoice_id, invoice.pk)

    def test_issue_conflicts_until_account_transaction_commits(self):
        invoice = self.make_invoice(owns_item=True)

        def issue():
            return self.request(
                "put", self.invoice_url("detail", invoice), {"status": "issued"}
            )

        self.assert_request_conflicts_until_commit(issue)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, "issued")

    def test_charge_update_conflicts_until_account_transaction_commits(self):
        def update_charge():
            return self.request(
                "put",
                reverse(
                    "charge_item-detail",
                    kwargs={
                        "facility_external_id": self.facility.external_id,
                        "external_id": self.item.external_id,
                    },
                ),
                {
                    "title": "Updated consultation",
                    "status": "billable",
                    "quantity": "1.00",
                    "unit_price_components": self.item.unit_price_components,
                },
            )

        self.assert_request_conflicts_until_commit(update_charge)
        self.item.refresh_from_db()
        self.assertEqual(self.item.title, "Updated consultation")
        self.assertEqual(self.item.status, "billable")
        self.assertIsNone(self.item.paid_invoice_id)

    def test_stale_billed_update_cannot_restore_status_after_invoice_removal(self):
        invoice = self.make_invoice(owns_item=True)
        loaded = Event()
        resume = Event()
        get_object = ChargeItemViewSet.get_object

        def pause_after_initial_read(view):
            instance = get_object(view)
            self.assertEqual(instance.status, "billed")
            loaded.set()
            self.assertTrue(resume.wait(timeout=15))
            return instance

        def update_charge():
            return self.request(
                "put",
                reverse(
                    "charge_item-detail",
                    kwargs={
                        "facility_external_id": self.facility.external_id,
                        "external_id": self.item.external_id,
                    },
                ),
                {
                    "title": "Stale invoice edit",
                    "status": "billed",
                    "quantity": "2.00",
                    "unit_price_components": self.item.unit_price_components,
                },
            )

        with (
            ThreadPoolExecutor(max_workers=1) as executor,
            patch.object(ChargeItemViewSet, "get_object", pause_after_initial_read),
        ):
            future = executor.submit(self.in_another_connection, update_charge)
            try:
                self.assertTrue(loaded.wait(timeout=10))
                response_status, data = self.request(
                    "post",
                    self.invoice_url("remove-item-from-invoice", invoice),
                    {"charge_item": str(self.item.external_id)},
                )
                self.assertEqual(response_status, status.HTTP_200_OK, data)
            finally:
                resume.set()
            response_status, data = future.result(timeout=15)
            self.assertEqual(response_status, status.HTTP_400_BAD_REQUEST, data)

        self.item.refresh_from_db()
        invoice.refresh_from_db()
        self.assertEqual(self.item.status, "billable")
        self.assertIsNone(self.item.paid_invoice_id)
        self.assertEqual(self.item.title, "Consultation")
        self.assertEqual(self.item.quantity, Decimal("1.00"))
        self.assertEqual(invoice.charge_items, [])
        self.assertEqual(invoice.total_gross, Decimal("0.00"))

    def test_second_creation_cannot_claim_item_before_first_invoice_commits(self):
        with ThreadPoolExecutor(max_workers=1) as executor:
            with transaction.atomic():
                response_status, data = self.create_invoice()
                self.assertEqual(response_status, status.HTTP_200_OK)
                future = executor.submit(
                    self.in_another_connection, self.create_invoice
                )
                response_status, _ = future.result(timeout=10)
                self.assertEqual(response_status, status.HTTP_423_LOCKED)
            future = executor.submit(self.in_another_connection, self.create_invoice)
            response_status, _ = future.result(timeout=10)
            self.assertEqual(response_status, status.HTTP_400_BAD_REQUEST)
        invoice = Invoice.objects.get(external_id=data["id"])
        self.item.refresh_from_db()
        self.assertEqual(Invoice.objects.count(), 1)
        self.assertEqual(invoice.charge_items, [self.item.pk])
        self.assertEqual(self.item.paid_invoice_id, invoice.pk)

    def test_cancellation_holds_account_until_callers_aborted_save_commits(self):
        invoice = self.make_invoice(owns_item=True)

        def issue():
            return self.request(
                "put", self.invoice_url("detail", invoice), {"status": "issued"}
            )

        with ThreadPoolExecutor(max_workers=1) as executor:
            with transaction.atomic():
                handle_charge_item_cancel(self.item)
                # The helper has returned, but its caller has not committed.
                self.item.status = "aborted"
                self.item.save()
                future = executor.submit(self.in_another_connection, issue)
                response_status, _ = future.result(timeout=10)
                self.assertEqual(response_status, status.HTTP_423_LOCKED)
            future = executor.submit(self.in_another_connection, issue)
            response_status, _ = future.result(timeout=10)
            self.assertEqual(response_status, status.HTTP_400_BAD_REQUEST)
        invoice.refresh_from_db()
        self.item.refresh_from_db()
        self.assertEqual(invoice.status, "draft")
        self.assertEqual(invoice.charge_items, [])
        self.assertEqual(self.item.status, "aborted")
        self.assertIsNone(self.item.paid_invoice_id)

    def test_stale_cancellation_cannot_abort_item_while_payment_commits(self):
        stale_item = ChargeItem.objects.get(pk=self.item.pk)
        self.assertIsNone(stale_item.paid_invoice_id)
        invoice = self.make_invoice(owns_item=True, invoice_status="issued")

        def cancel_charge():
            with transaction.atomic():
                handle_charge_item_cancel(stale_item)
                stale_item.status = "aborted"
                stale_item.save()

        with ThreadPoolExecutor(max_workers=1) as executor:
            with transaction.atomic():
                response_status, _ = self.request(
                    "put", self.invoice_url("detail", invoice), {"status": "balanced"}
                )
                self.assertEqual(response_status, status.HTTP_200_OK)
                future = executor.submit(self.in_another_connection, cancel_charge)
                with self.assertRaises(ObjectLocked):
                    future.result(timeout=5)
            future = executor.submit(self.in_another_connection, cancel_charge)
            with self.assertRaises(ValidationError):
                future.result(timeout=5)
        invoice.refresh_from_db()
        self.item.refresh_from_db()
        self.assertEqual(invoice.status, "balanced")
        self.assertEqual(invoice.charge_items_copy[0]["status"], "billed")
        self.assertEqual(self.item.status, "paid")
        self.assertEqual(self.item.paid_invoice_id, invoice.pk)
