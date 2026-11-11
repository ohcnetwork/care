from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from django.db import close_old_connections, connections, transaction
from django.test import TransactionTestCase, skipUnlessDBFeature
from django.urls import reverse
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from care.emr.models.account import Account
from care.emr.models.charge_item import ChargeItem
from care.emr.models.facility_config import FacilityMonetoryConfig
from care.emr.models.invoice import Invoice
from care.emr.resources.invoice.return_items_invoice import generate_return_invoice
from care.utils.lock import ObjectLocked


@skipUnlessDBFeature("has_select_for_update_nowait", "has_select_for_no_key_update")
class InvoiceNumberLockTests(TransactionTestCase):
    def setUp(self):
        self.user = baker.make("users.User", is_superuser=True)
        self.facility = self.make_facility()
        self.first = self.make_charge(self.facility)
        self.second = self.make_charge(self.facility)

    def make_facility(self):
        facility = baker.make("facility.Facility", created_by=self.user)
        FacilityMonetoryConfig.objects.update_or_create(
            facility=facility,
            defaults={"invoice_number_expression": 'f"INV-{invoice_count + 1}"'},
        )
        return facility

    def make_charge(self, facility):
        patient = baker.make("emr.Patient")
        account = baker.make(
            Account,
            facility=facility,
            patient=patient,
            status="active",
            billing_status="open",
        )
        return baker.make(
            ChargeItem,
            facility=facility,
            patient=patient,
            account=account,
            status="billable",
            quantity=1,
            total_price=Decimal(100),
            unit_price_components=[
                {"amount": "100", "monetary_component_type": "base"}
            ],
            total_price_components=[
                {"amount": "100", "monetary_component_type": "base"}
            ],
        )

    def create_invoice(self, item):
        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.post(
            reverse(
                "invoice-list",
                kwargs={"facility_external_id": item.facility.external_id},
            ),
            {
                "account": str(item.account.external_id),
                "status": "draft",
                "charge_items": [str(item.external_id)],
            },
            format="json",
        )
        return response.status_code, response.data

    def create_in_another_connection(self, item):
        close_old_connections()
        try:
            return self.create_invoice(item)
        finally:
            connections["default"].close()

    def test_other_account_cannot_allocate_number_until_first_invoice_commits(self):
        with ThreadPoolExecutor(max_workers=1) as executor:
            with transaction.atomic():
                first_status, first_data = self.create_invoice(self.first)
                self.assertEqual(first_status, status.HTTP_200_OK)
                self.assertEqual(first_data["number"], "INV-1")
                future = executor.submit(self.create_in_another_connection, self.second)
                second_status, _ = future.result(timeout=10)
                self.assertEqual(second_status, status.HTTP_423_LOCKED)
                self.second.refresh_from_db()
                self.assertEqual(self.second.status, "billable")
                self.assertIsNone(self.second.paid_invoice_id)
            future = executor.submit(self.create_in_another_connection, self.second)
            second_status, second_data = future.result(timeout=10)
            self.assertEqual(second_status, status.HTTP_200_OK)
            self.assertEqual(second_data["number"], "INV-2")
        self.assertEqual(Invoice.objects.count(), 2)
        self.assertNotEqual(first_data["id"], second_data["id"])

    def test_other_facility_can_allocate_its_number_concurrently(self):
        other = self.make_charge(self.make_facility())
        with ThreadPoolExecutor(max_workers=1) as executor, transaction.atomic():
            first_status, first_data = self.create_invoice(self.first)
            self.assertEqual(first_status, status.HTTP_200_OK)
            future = executor.submit(self.create_in_another_connection, other)
            other_status, other_data = future.result(timeout=10)
            self.assertEqual(other_status, status.HTTP_200_OK)
            self.assertEqual(first_data["number"], "INV-1")
            self.assertEqual(other_data["number"], "INV-1")
        self.assertEqual(Invoice.objects.count(), 2)

    def test_refund_and_regular_invoice_share_the_facility_number_lock(self):
        location = baker.make("emr.FacilityLocation", facility=self.facility)
        definition = baker.make(
            "emr.ChargeItemDefinition",
            facility=self.facility,
            slug=f"f-{self.facility.external_id}-numbered-return",
            title="Returned product",
            price_components=[{"amount": "100", "monetary_component_type": "base"}],
        )
        product = baker.make(
            "emr.Product",
            facility=self.facility,
            product_knowledge=baker.make(
                "emr.ProductKnowledge", facility=self.facility
            ),
            charge_item_definition=definition,
        )
        order = baker.make(
            "emr.DeliveryOrder",
            destination=location,
            patient=self.second.patient,
            created_by=self.user,
            updated_by=self.user,
        )
        baker.make(
            "emr.SupplyDelivery",
            order=order,
            supplied_item=product,
            supplied_item_quantity=1,
            status="completed",
        )

        def create_refund():
            close_old_connections()
            try:
                return generate_return_invoice(order)
            finally:
                connections["default"].close()

        with ThreadPoolExecutor(max_workers=1) as executor:
            with transaction.atomic():
                first_status, first_data = self.create_invoice(self.first)
                self.assertEqual(first_status, status.HTTP_200_OK)
                self.assertEqual(first_data["number"], "INV-1")
                future = executor.submit(create_refund)
                with self.assertRaises(ObjectLocked):
                    future.result(timeout=10)
            future = executor.submit(create_refund)
            refund = future.result(timeout=10)
            self.assertTrue(refund.is_refund)
            self.assertEqual(refund.number, "INV-2")
        self.assertEqual(Invoice.objects.count(), 2)

    def test_rollback_releases_number_and_charge_for_retry(self):
        with self.assertRaisesMessage(ValueError, "rollback"), transaction.atomic():
            first_status, first_data = self.create_invoice(self.first)
            self.assertEqual(first_status, status.HTTP_200_OK)
            self.assertEqual(first_data["number"], "INV-1")
            raise ValueError("rollback")
        self.first.refresh_from_db()
        self.assertIsNone(self.first.paid_invoice_id)
        self.assertEqual(self.first.status, "billable")
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.create_in_another_connection, self.second)
            second_status, second_data = future.result(timeout=10)
            self.assertEqual(second_status, status.HTTP_200_OK)
            self.assertEqual(second_data["number"], "INV-1")
        self.assertEqual(Invoice.objects.count(), 1)
