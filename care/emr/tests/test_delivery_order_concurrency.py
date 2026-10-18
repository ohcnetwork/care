from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from types import SimpleNamespace

from django.db import close_old_connections, connections, transaction
from django.test import TransactionTestCase, skipUnlessDBFeature
from model_bakery import baker
from rest_framework.exceptions import ValidationError

from care.emr.api.viewsets.inventory.delivery_order import DeliveryOrderViewSet
from care.emr.api.viewsets.inventory.supply_delivery import SupplyDeliveryViewSet
from care.emr.locks.billing import InventoryItemLock
from care.emr.models.inventory_item import InventoryItem
from care.emr.models.supply_delivery import DeliveryOrder, SupplyDelivery
from care.emr.resources.inventory.inventory_item.sync_inventory_item import (
    sync_inventory_item,
)
from care.utils.lock import ObjectLocked


@skipUnlessDBFeature("has_select_for_update_nowait")
class DeliveryOrderConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.user = baker.make("users.User")
        self.facility = baker.make("facility.Facility", created_by=self.user)
        self.origin = baker.make("emr.FacilityLocation", facility=self.facility)
        self.destination = baker.make("emr.FacilityLocation", facility=self.facility)
        self.product = self.create_product()
        self.origin_item = self.seed_stock(self.origin, self.product)
        self.destination_item = self.seed_stock(self.destination, self.product)
        self.other_item = self.seed_stock(self.origin, self.create_product())
        self.order = baker.make(
            DeliveryOrder,
            origin=self.origin,
            destination=self.destination,
            status="in_progress",
        )

    def create_product(self):
        knowledge = baker.make("emr.ProductKnowledge", facility=self.facility)
        return baker.make(
            "emr.Product", facility=self.facility, product_knowledge=knowledge
        )

    def seed_stock(self, location, product):
        item = baker.make(
            InventoryItem,
            location=location,
            product=product,
            net_content=500,
            status="active",
        )
        order = baker.make(DeliveryOrder, destination=location, status="in_progress")
        baker.make(
            SupplyDelivery,
            order=order,
            supplied_item=product,
            supplied_inventory_item=item,
            supplied_item_quantity=500,
            status="completed",
        )
        return item

    def view(self, cls):
        view = cls()
        view.request = SimpleNamespace(user=self.user, data={})
        return view

    def run_in_another_connection(self, operation):
        close_old_connections()
        try:
            return operation()
        finally:
            connections["default"].close()

    def create_delivery(self, item=None):
        instance = SupplyDelivery(
            order=DeliveryOrder.objects.get(pk=self.order.pk),
            supplied_inventory_item=InventoryItem.objects.get(
                pk=(item or self.origin_item).pk
            ),
            supplied_item_quantity=100,
            status="in_progress",
            supplied_item_condition="normal",
            delivery_type="product",
        )
        self.view(SupplyDeliveryViewSet).perform_create(instance)
        return instance

    def complete_delivery(self, delivery):
        instance = SupplyDelivery.objects.get(pk=delivery.pk)
        instance.status = "completed"
        self.view(SupplyDeliveryViewSet).perform_update(instance)

    def cancel(self):
        instance = DeliveryOrder.objects.get(pk=self.order.pk)
        instance.status = "abandoned"
        self.view(DeliveryOrderViewSet).perform_update(instance)

    def assert_stock(self, item, quantity):
        item.refresh_from_db()
        self.assertEqual(item.net_content, Decimal(quantity))
        sync_inventory_item(inventory_item=item)
        item.refresh_from_db()
        self.assertEqual(item.net_content, Decimal(quantity))

    def test_cancellation_conflicts_with_uncommitted_new_child_then_retry_cancels_it(
        self,
    ):
        with ThreadPoolExecutor(max_workers=1) as executor:
            with transaction.atomic():
                delivery = self.create_delivery()
                future = executor.submit(self.run_in_another_connection, self.cancel)
                with self.assertRaises(ObjectLocked):
                    future.result(timeout=5)

            executor.submit(self.run_in_another_connection, self.cancel).result(
                timeout=5
            )

        self.order.refresh_from_db()
        delivery.refresh_from_db()
        self.assertEqual(self.order.status, "abandoned")
        self.assertEqual(delivery.status, "abandoned")
        self.assert_stock(self.origin_item, 500)
        self.assert_stock(self.destination_item, 500)

    def test_completion_waits_for_child_creation_then_requires_completed_child(self):
        def complete_order():
            instance = DeliveryOrder.objects.get(pk=self.order.pk)
            instance.status = "completed"
            self.view(DeliveryOrderViewSet).perform_update(instance)

        with ThreadPoolExecutor(max_workers=1) as executor:
            with transaction.atomic():
                delivery = self.create_delivery()
                future = executor.submit(self.run_in_another_connection, complete_order)
                with self.assertRaises(ObjectLocked):
                    future.result(timeout=5)

            future = executor.submit(self.run_in_another_connection, complete_order)
            with self.assertRaisesMessage(
                ValidationError, "Finalise Deliveries before completing order"
            ):
                future.result(timeout=5)

            self.order.refresh_from_db()
            delivery.refresh_from_db()
            self.assertEqual(self.order.status, "in_progress")
            self.assertEqual(delivery.status, "in_progress")

            self.complete_delivery(delivery)
            executor.submit(self.run_in_another_connection, complete_order).result(
                timeout=5
            )

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "completed")
        self.assert_stock(self.origin_item, 400)
        self.assert_stock(self.destination_item, 600)

    def test_empty_order_cancellation_blocks_new_child_on_different_stock(self):
        def create():
            return self.create_delivery(self.other_item)

        with ThreadPoolExecutor(max_workers=1) as executor:
            with transaction.atomic():
                self.cancel()
                future = executor.submit(self.run_in_another_connection, create)
                with self.assertRaises(ValidationError):
                    future.result(timeout=5)

            future = executor.submit(self.run_in_another_connection, create)
            with self.assertRaisesMessage(
                ValidationError, "Delivery order is abandoned or entered in error"
            ):
                future.result(timeout=5)

        self.assertFalse(SupplyDelivery.objects.filter(order=self.order).exists())
        self.assert_stock(self.origin_item, 500)
        self.assert_stock(self.destination_item, 500)
        self.assert_stock(self.other_item, 500)

    def test_child_completion_blocks_cancellation_until_commit_then_reverts_stock(
        self,
    ):
        delivery = self.create_delivery()
        with ThreadPoolExecutor(max_workers=1) as executor:
            with transaction.atomic():
                self.complete_delivery(delivery)
                future = executor.submit(self.run_in_another_connection, self.cancel)
                with self.assertRaises(ObjectLocked):
                    future.result(timeout=5)

            self.assert_stock(self.origin_item, 400)
            self.assert_stock(self.destination_item, 600)
            executor.submit(self.run_in_another_connection, self.cancel).result(
                timeout=5
            )

        delivery.refresh_from_db()
        self.assertEqual(delivery.status, "abandoned")
        self.assert_stock(self.origin_item, 500)
        self.assert_stock(self.destination_item, 500)

    def test_cancellation_blocks_child_completion_then_rejects_it_after_commit(self):
        delivery = self.create_delivery()

        def complete():
            return self.complete_delivery(delivery)

        with ThreadPoolExecutor(max_workers=1) as executor:
            with transaction.atomic():
                self.cancel()
                future = executor.submit(self.run_in_another_connection, complete)
                with self.assertRaises(ObjectLocked):
                    future.result(timeout=5)

            future = executor.submit(self.run_in_another_connection, complete)
            with self.assertRaisesMessage(
                ValidationError, "Delivery order is abandoned or entered in error"
            ):
                future.result(timeout=5)

        delivery.refresh_from_db()
        self.assertEqual(delivery.status, "abandoned")
        self.assert_stock(self.origin_item, 500)
        self.assert_stock(self.destination_item, 500)

    def test_failed_inventory_lock_rolls_back_cancellation_and_allows_retry(self):
        delivery = self.create_delivery()
        with ThreadPoolExecutor(max_workers=1) as executor:
            with InventoryItemLock(self.destination_item):
                future = executor.submit(self.run_in_another_connection, self.cancel)
                with self.assertRaises(ObjectLocked):
                    future.result(timeout=5)

                self.order.refresh_from_db()
                delivery.refresh_from_db()
                self.assertEqual(self.order.status, "in_progress")
                self.assertEqual(delivery.status, "in_progress")

            self.assert_stock(self.origin_item, 400)
            self.assert_stock(self.destination_item, 500)
            executor.submit(self.run_in_another_connection, self.cancel).result(
                timeout=5
            )

        self.order.refresh_from_db()
        delivery.refresh_from_db()
        self.assertEqual(self.order.status, "abandoned")
        self.assertEqual(delivery.status, "abandoned")
        self.assert_stock(self.origin_item, 500)
        self.assert_stock(self.destination_item, 500)
