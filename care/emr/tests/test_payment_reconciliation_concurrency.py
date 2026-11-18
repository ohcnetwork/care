from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from functools import wraps
from threading import Event
from unittest.mock import patch

from django.db import close_old_connections, connections
from django.test import TransactionTestCase, skipUnlessDBFeature
from django.urls import reverse
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from care.emr.api.viewsets.base import EMRUpdateMixin
from care.emr.api.viewsets.payment_reconciliation import PaymentReconciliationViewSet
from care.emr.locks.billing import AccountLock
from care.emr.models.account import Account
from care.emr.models.invoice import Invoice
from care.emr.models.payment_reconciliation import PaymentReconciliation
from care.emr.resources.account.sync_items import rebalance_account_task


@skipUnlessDBFeature("has_select_for_update_nowait", "has_select_for_no_key_update")
class PaymentReconciliationConcurrencyTests(TransactionTestCase):
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
        self.account = self.make_account()
        self.payment = self.make_payment(self.account)
        rebalance_account_task(self.account.pk)

    def make_payment(self, account, **kwargs):
        return baker.make(
            PaymentReconciliation,
            facility=self.facility,
            account=account,
            reconciliation_type="payment",
            kind="deposit",
            issuer_type="patient",
            outcome="complete",
            method="cash",
            amount=Decimal("100.00"),
            tendered_amount=Decimal("100.00"),
            returned_amount=Decimal("0.00"),
            is_credit_note=False,
            **{"status": "active", **kwargs},
        )

    def make_account(self):
        return baker.make(
            Account,
            facility=self.facility,
            patient=self.patient,
            status="active",
            billing_status="open",
        )

    def in_another_connection(self, operation):
        close_old_connections()
        try:
            return operation()
        finally:
            connections["default"].close()

    def request(self, method, action, data, *, detail=True):
        kwargs = {"facility_external_id": self.facility.external_id}
        if detail:
            kwargs["external_id"] = self.payment.external_id
        client = APIClient()
        client.force_authenticate(user=self.user)
        response = getattr(client, method)(
            reverse(f"payment_reconciliation-{action}", kwargs=kwargs),
            data,
            format="json",
        )
        return response.status_code, response.data

    def update_payment(self):
        return self.request(
            "put",
            "detail",
            {
                "status": "active",
                "reconciliation_type": "payment",
                "kind": "deposit",
                "issuer_type": "patient",
                "outcome": "complete",
                "method": "cash",
                "note": "Edited note",
            },
        )

    def cancel_payment(self, reason="cancelled"):
        return self.request("post", "cancel-payment-reconciliation", {"reason": reason})

    def transfer_payment(self, account, payments=None):
        payments = payments or [self.payment]
        return self.request(
            "post",
            "change-account",
            {
                "payment_reconciliations": [str(item.external_id) for item in payments],
                "target_account": str(account.external_id),
            },
            detail=False,
        )

    def assert_cancelled_payment(self, reason="cancelled"):
        self.payment.refresh_from_db()
        self.account.refresh_from_db()
        self.assertEqual(self.payment.status, reason)
        self.assertEqual(self.account.total_paid, Decimal("0.00"))

    def test_edit_serializes_cancellation_and_account_transfer(self):
        validated = Event()
        resume = Event()
        perform_update = EMRUpdateMixin.perform_update
        target = self.make_account()

        def pause_before_save(view, instance):
            if isinstance(view, PaymentReconciliationViewSet):
                validated.set()
                self.assertTrue(resume.wait(timeout=15))
            return perform_update(view, instance)

        with (
            ThreadPoolExecutor(max_workers=1) as executor,
            patch.object(EMRUpdateMixin, "perform_update", pause_before_save),
        ):
            future = executor.submit(self.in_another_connection, self.update_payment)
            try:
                self.assertTrue(validated.wait(timeout=10))
                response_status, _ = self.cancel_payment()
                self.assertEqual(response_status, status.HTTP_423_LOCKED)
                response_status, _ = self.transfer_payment(target)
                self.assertEqual(response_status, status.HTTP_423_LOCKED)
            finally:
                resume.set()
            response_status, data = future.result(timeout=15)
            self.assertEqual(response_status, status.HTTP_200_OK, data)

        response_status, data = self.cancel_payment()
        self.assertEqual(response_status, status.HTTP_200_OK, data)
        self.assert_cancelled_payment()
        self.assertEqual(self.payment.account_id, self.account.pk)
        self.assertEqual(self.payment.note, "Edited note")

    def test_stale_edit_cannot_reactivate_committed_cancellation(self):
        for reason in ["cancelled", "entered_in_error"]:
            with self.subTest(reason=reason):
                if reason == "entered_in_error":
                    self.payment = self.make_payment(self.account)
                    rebalance_account_task(self.account.pk)
                self.assert_stale_edit_rejected_after_cancellation(reason)

    def assert_stale_edit_rejected_after_cancellation(self, reason):
        loaded = Event()
        resume = Event()
        get_object = PaymentReconciliationViewSet.get_object

        def pause_after_initial_read(view):
            instance = get_object(view)
            if view.action == "update" and not loaded.is_set():
                self.assertEqual(instance.status, "active")
                loaded.set()
                self.assertTrue(resume.wait(timeout=15))
            return instance

        with (
            ThreadPoolExecutor(max_workers=1) as executor,
            patch.object(
                PaymentReconciliationViewSet, "get_object", pause_after_initial_read
            ),
        ):
            future = executor.submit(self.in_another_connection, self.update_payment)
            try:
                self.assertTrue(loaded.wait(timeout=10))
                response_status, data = self.cancel_payment(reason)
                self.assertEqual(response_status, status.HTTP_200_OK, data)
                self.assert_cancelled_payment(reason)
            finally:
                resume.set()
            response_status, data = future.result(timeout=15)
            self.assertEqual(response_status, status.HTTP_400_BAD_REQUEST, data)

        self.assert_cancelled_payment(reason)

    def test_cancellation_keeps_lock_until_request_commit(self):
        cancelled = Event()
        resume = Event()
        cancel = PaymentReconciliationViewSet.cancel_payment_reconciliation
        target = self.make_account()

        @wraps(cancel)
        def pause_after_cancel(view, request, *args, **kwargs):
            response = cancel(view, request, *args, **kwargs)
            cancelled.set()
            self.assertTrue(resume.wait(timeout=15))
            return response

        with (
            ThreadPoolExecutor(max_workers=1) as executor,
            patch.object(
                PaymentReconciliationViewSet,
                "cancel_payment_reconciliation",
                pause_after_cancel,
            ),
        ):
            future = executor.submit(self.in_another_connection, self.cancel_payment)
            try:
                self.assertTrue(cancelled.wait(timeout=10))
                response_status, _ = self.update_payment()
                self.assertEqual(response_status, status.HTTP_423_LOCKED)
                response_status, _ = self.transfer_payment(target)
                self.assertEqual(response_status, status.HTTP_423_LOCKED)
            finally:
                resume.set()
            response_status, data = future.result(timeout=15)
            self.assertEqual(response_status, status.HTTP_200_OK, data)

        self.assert_cancelled_payment()
        response_status, _ = self.update_payment()
        self.assertEqual(response_status, status.HTTP_400_BAD_REQUEST)

    def test_stale_account_transfer_rejects_changed_source(self):
        loaded = Event()
        resume = Event()
        first_target = self.make_account()
        stale_target = self.make_account()

        def pause_before_first_lock(accounts):
            if not loaded.is_set():
                loaded.set()
                self.assertTrue(resume.wait(timeout=15))
            return AccountLock(accounts)

        with (
            ThreadPoolExecutor(max_workers=1) as executor,
            patch(
                "care.emr.api.viewsets.payment_reconciliation.AccountLock",
                side_effect=pause_before_first_lock,
            ),
        ):
            future = executor.submit(
                self.in_another_connection,
                lambda: self.transfer_payment(stale_target),
            )
            try:
                self.assertTrue(loaded.wait(timeout=10))
                response_status, data = self.transfer_payment(first_target)
                self.assertEqual(response_status, status.HTTP_201_CREATED, data)
            finally:
                resume.set()
            response_status, data = future.result(timeout=15)
            self.assertEqual(response_status, status.HTTP_423_LOCKED, data)

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.account_id, first_target.pk)
        for account, total_paid in [
            (self.account, Decimal("0.00")),
            (first_target, Decimal("100.00")),
            (stale_target, Decimal("0.00")),
        ]:
            account.refresh_from_db()
            self.assertEqual(account.total_paid, total_paid)

    def test_account_transfer_deduplicates_payments_from_multiple_sources(self):
        second_source = self.make_account()
        target = self.make_account()
        second_payment = self.make_payment(second_source)
        rebalance_account_task(second_source.pk)

        response_status, data = self.transfer_payment(
            target, [self.payment, second_payment, self.payment]
        )
        self.assertEqual(response_status, status.HTTP_201_CREATED, data)
        for payment in [self.payment, second_payment]:
            payment.refresh_from_db()
            self.assertEqual(payment.account_id, target.pk)
        for account, total_paid in [
            (self.account, Decimal("0.00")),
            (second_source, Decimal("0.00")),
            (target, Decimal("200.00")),
        ]:
            account.refresh_from_db()
            self.assertEqual(account.total_paid, total_paid)

    def test_stale_edit_and_cancellation_reject_changed_account(self):
        get_object = PaymentReconciliationViewSet.get_object
        for operation in [self.update_payment, self.cancel_payment]:
            with self.subTest(operation=operation.__name__):
                if operation == self.cancel_payment:
                    self.payment = self.make_payment(self.account)
                    rebalance_account_task(self.account.pk)
                target = self.make_account()
                loaded = Event()
                resume = Event()

                def pause_after_initial_read(view, loaded=loaded, resume=resume):
                    instance = get_object(view)
                    if not loaded.is_set():
                        loaded.set()
                        self.assertTrue(resume.wait(timeout=15))
                    return instance

                with (
                    ThreadPoolExecutor(max_workers=1) as executor,
                    patch.object(
                        PaymentReconciliationViewSet,
                        "get_object",
                        pause_after_initial_read,
                    ),
                ):
                    future = executor.submit(self.in_another_connection, operation)
                    try:
                        self.assertTrue(loaded.wait(timeout=10))
                        response_status, data = self.transfer_payment(target)
                        self.assertEqual(response_status, status.HTTP_201_CREATED, data)
                    finally:
                        resume.set()
                    response_status, data = future.result(timeout=15)
                    self.assertEqual(response_status, status.HTTP_423_LOCKED, data)

                self.payment.refresh_from_db()
                self.account.refresh_from_db()
                target.refresh_from_db()
                self.assertEqual(self.payment.status, "active")
                self.assertEqual(self.payment.account_id, target.pk)
                self.assertEqual(self.account.total_paid, Decimal("0.00"))
                self.assertEqual(target.total_paid, Decimal("100.00"))

    def test_invalid_later_payment_rolls_back_entire_account_transfer(self):
        target = self.make_account()
        invoice = baker.make(
            Invoice,
            facility=self.facility,
            patient=self.patient,
            account=self.account,
            status="issued",
            total_gross=Decimal("0.00"),
        )
        for invalid_fields in [
            {"status": "cancelled"},
            {"target_invoice": invoice},
        ]:
            with self.subTest(invalid_fields=invalid_fields):
                rejected = self.make_payment(self.account, **invalid_fields)
                rebalance_account_task(self.account.pk)
                self.account.refresh_from_db()
                original_total = self.account.total_paid
                manager = PaymentReconciliation.objects
                get_queryset = manager.get_queryset
                with patch.object(
                    manager,
                    "get_queryset",
                    side_effect=lambda get_queryset=get_queryset: get_queryset().order_by(
                        "pk"
                    ),
                ):
                    response_status, data = self.transfer_payment(
                        target, [self.payment, rejected]
                    )
                self.assertEqual(response_status, status.HTTP_400_BAD_REQUEST, data)
                for payment in [self.payment, rejected]:
                    payment.refresh_from_db()
                    self.assertEqual(payment.account_id, self.account.pk)
                self.account.refresh_from_db()
                target.refresh_from_db()
                self.assertEqual(self.account.total_paid, original_total)
                self.assertEqual(target.total_paid, Decimal("0.00"))
