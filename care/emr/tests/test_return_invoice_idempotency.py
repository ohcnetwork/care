from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from django.db import close_old_connections, connections, transaction
from django.test import TransactionTestCase, skipUnlessDBFeature
from model_bakery import baker
from rest_framework.test import APIRequestFactory, force_authenticate

from care.emr.api.viewsets.inventory.delivery_order import DeliveryOrderViewSet
from care.emr.models.charge_item import ChargeItem
from care.emr.models.invoice import Invoice
from care.emr.models.supply_delivery import DeliveryOrder
from care.emr.resources.invoice.return_items_invoice import generate_return_invoice
from care.utils.lock import ObjectLocked
from care.utils.tests.base import CareAPITestBase


class ReturnInvoiceFixtures:
    def setUp(self):
        super().setUp()
        self.user = baker.make("users.User", is_superuser=True)
        self.facility = baker.make("facility.Facility", created_by=self.user)
        self.patient = baker.make("emr.Patient")
        self.location = baker.make("emr.FacilityLocation", facility=self.facility)
        definition = baker.make(
            "emr.ChargeItemDefinition",
            facility=self.facility,
            status="active",
            title="Returned item",
            slug=f"f-{self.facility.external_id}-returned-item",
            price_components=[
                {"monetary_component_type": "base", "currency": "INR", "amount": "100"}
            ],
        )
        knowledge = baker.make("emr.ProductKnowledge", facility=self.facility)
        product = baker.make(
            "emr.Product",
            facility=self.facility,
            product_knowledge=knowledge,
            charge_item_definition=definition,
            status="active",
            product_type="medication",
        )
        self.stock = baker.make(
            "emr.InventoryItem",
            location=self.location,
            product=product,
            net_content=Decimal(1),
            status="active",
        )
        self.order = baker.make(
            DeliveryOrder,
            name="Patient return",
            status="in_progress",
            origin=None,
            destination=self.location,
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user,
        )
        self.delivery = baker.make(
            "emr.SupplyDelivery",
            order=self.order,
            supplied_item=product,
            supplied_inventory_item=self.stock,
            supplied_item_quantity=1,
            supplied_item_condition="normal",
            delivery_type="product",
            status="completed",
        )

    def update_order(self, status):
        request = APIRequestFactory().put(
            "/delivery-order/",
            {"name": self.order.name, "status": status},
            format="json",
        )
        force_authenticate(request, user=self.user)
        return DeliveryOrderViewSet.as_view({"put": "update"})(
            request, external_id=str(self.order.external_id)
        )

    def complete_order(self):
        response = self.update_order("completed")
        self.assertEqual(response.status_code, 200, response.data)
        self.order.refresh_from_db()
        return self.order.patient_invoice

    def assert_single_refund(self, invoice):
        self.assertEqual(Invoice.objects.filter(patient=self.patient).count(), 1)
        self.assertEqual(ChargeItem.objects.filter(patient=self.patient).count(), 1)
        invoice.refresh_from_db()
        self.assertEqual(invoice.total_gross, Decimal(-100))
        item = ChargeItem.objects.get(pk=invoice.charge_items[0])
        self.assertEqual(item.account_id, invoice.account_id)


class ReturnInvoiceIdempotencyTests(ReturnInvoiceFixtures, CareAPITestBase):
    def test_completed_return_cannot_be_reopened_or_refunded_twice(self):
        invoice = self.complete_order()

        for status in ["draft", "pending", "in_progress"]:
            with self.subTest(status=status):
                response = self.update_order(status)
                self.assertEqual(response.status_code, 400, response.data)
                self.assertIn(
                    "Completed delivery order can only be cancelled", str(response.data)
                )
                self.order.refresh_from_db()
                self.assertEqual(self.order.status, "completed")
                self.assertEqual(self.order.patient_invoice_id, invoice.pk)

        response = self.update_order("completed")
        self.assertEqual(response.status_code, 200, response.data)
        self.assert_single_refund(invoice)
        self.assertEqual(invoice.status, "issued")

    def test_generation_retries_use_existing_invoice_from_a_fresh_locked_order(self):
        stale_order = DeliveryOrder.objects.get(pk=self.order.pk)
        self.assertIsNone(stale_order.patient_invoice_id)
        invoice = self.complete_order()

        first_retry = generate_return_invoice(stale_order)
        second_retry = generate_return_invoice(
            DeliveryOrder.objects.get(pk=self.order.pk)
        )

        self.assertEqual(first_retry.pk, invoice.pk)
        self.assertEqual(second_retry.pk, invoice.pk)
        self.assertEqual(stale_order.patient_invoice_id, invoice.pk)
        self.assert_single_refund(invoice)

    def test_completed_return_can_be_cancelled_without_regenerating_its_refund(self):
        stale_order = DeliveryOrder.objects.get(pk=self.order.pk)
        invoice = self.complete_order()

        response = self.update_order("entered_in_error")

        self.assertEqual(response.status_code, 200, response.data)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "entered_in_error")
        self.assert_single_refund(invoice)
        self.assertEqual(invoice.status, "cancelled")
        item = ChargeItem.objects.get(pk=invoice.charge_items[0])
        self.assertEqual(item.status, "entered_in_error")
        self.assertIsNone(item.paid_invoice_id)
        self.delivery.refresh_from_db()
        self.assertEqual(self.delivery.status, "entered_in_error")
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.net_content, Decimal(0))

        retry = generate_return_invoice(stale_order)
        self.assertEqual(retry.pk, invoice.pk)
        self.assert_single_refund(invoice)
        self.assertEqual(retry.status, "cancelled")


@skipUnlessDBFeature("has_select_for_update_nowait", "has_select_for_no_key_update")
class ReturnInvoiceConcurrencyTests(ReturnInvoiceFixtures, TransactionTestCase):
    def generate_in_another_connection(self):
        close_old_connections()
        try:
            order = DeliveryOrder.objects.get(pk=self.order.pk)
            return generate_return_invoice(order).pk
        finally:
            connections["default"].close()

    def test_generation_conflicts_until_first_completion_commits_then_reuses_invoice(
        self,
    ):
        with ThreadPoolExecutor(max_workers=1) as executor:
            with transaction.atomic():
                invoice = self.complete_order()
                future = executor.submit(self.generate_in_another_connection)
                with self.assertRaises(ObjectLocked):
                    future.result(timeout=5)

            future = executor.submit(self.generate_in_another_connection)
            self.assertEqual(future.result(timeout=5), invoice.pk)

        self.assert_single_refund(invoice)
        self.assertEqual(invoice.status, "issued")
