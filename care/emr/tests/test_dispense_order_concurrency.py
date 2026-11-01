from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from types import SimpleNamespace

from django.db import close_old_connections, connections, transaction
from django.test import TransactionTestCase, skipUnlessDBFeature
from model_bakery import baker
from rest_framework.exceptions import ValidationError

from care.emr.api.viewsets.inventory.dispense_order import DispenseOrderViewSet
from care.emr.api.viewsets.medication_dispense import MedicationDispenseViewSet
from care.emr.models.inventory_item import InventoryItem
from care.emr.models.medication_dispense import DispenseOrder, MedicationDispense
from care.emr.resources.inventory.inventory_item.sync_inventory_item import (
    sync_inventory_item,
)
from care.emr.resources.medication.dispense.spec import MedicationDispenseUpdateSpec
from care.utils.lock import ObjectLocked


@skipUnlessDBFeature("has_select_for_update_nowait")
class DispenseOrderConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.user = baker.make("users.User")
        self.facility = baker.make("facility.Facility", created_by=self.user)
        self.location = baker.make("emr.FacilityLocation", facility=self.facility)
        self.patient = baker.make("emr.Patient")
        self.encounter = baker.make(
            "emr.Encounter", patient=self.patient, facility=self.facility
        )
        self.item = self.seed_stock()
        self.other_item = self.seed_stock()
        self.order = self.create_order()

    def seed_stock(self):
        knowledge = baker.make("emr.ProductKnowledge", facility=self.facility)
        product = baker.make(
            "emr.Product", facility=self.facility, product_knowledge=knowledge
        )
        item = baker.make(
            InventoryItem,
            location=self.location,
            product=product,
            net_content=500,
            status="active",
        )
        delivery_order = baker.make("emr.DeliveryOrder", destination=self.location)
        baker.make(
            "emr.SupplyDelivery",
            order=delivery_order,
            supplied_item=product,
            supplied_inventory_item=item,
            supplied_item_quantity=500,
            status="completed",
        )
        return item

    def create_order(self):
        return baker.make(
            DispenseOrder,
            patient=self.patient,
            facility=self.facility,
            location=self.location,
            status="in_progress",
        )

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

    def create_dispense(self, item=None):
        instance = MedicationDispense(
            patient=self.patient,
            encounter=self.encounter,
            location=self.location,
            item=InventoryItem.objects.get(pk=(item or self.item).pk),
            order=DispenseOrder.objects.get(pk=self.order.pk),
            quantity=100,
            status="in_progress",
        )
        instance._fully_dispensed = None  # noqa: SLF001
        self.view(MedicationDispenseViewSet).perform_create(instance)
        return instance

    def cancel(self, order=None):
        instance = DispenseOrder.objects.get(pk=(order or self.order).pk)
        instance.status = "abandoned"
        self.view(DispenseOrderViewSet).perform_update(instance)

    def deserialize_update(self, dispense, **data):
        return MedicationDispenseUpdateSpec.model_validate(data).de_serialize(
            obj=dispense
        )

    def reassign(self, dispense, order):
        instance = self.deserialize_update(
            MedicationDispense.objects.get(pk=dispense.pk),
            status="completed",
            order=str(order.external_id),
        )
        self.view(MedicationDispenseViewSet).perform_update(instance)

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
                dispense = self.create_dispense()
                future = executor.submit(self.run_in_another_connection, self.cancel)
                with self.assertRaises(ObjectLocked):
                    future.result(timeout=5)

            executor.submit(self.run_in_another_connection, self.cancel).result(
                timeout=5
            )

        self.order.refresh_from_db()
        dispense.refresh_from_db()
        self.assertEqual(self.order.status, "abandoned")
        self.assertEqual(dispense.status, "cancelled")
        self.assert_stock(self.item, 500)

    def test_empty_order_cancellation_blocks_new_child_until_cancel_is_committed(self):
        def create():
            return self.create_dispense(self.other_item)

        with ThreadPoolExecutor(max_workers=1) as executor:
            with transaction.atomic():
                self.cancel()
                future = executor.submit(self.run_in_another_connection, create)
                with self.assertRaises(ObjectLocked):
                    future.result(timeout=5)

            future = executor.submit(self.run_in_another_connection, create)
            with self.assertRaisesMessage(
                ValidationError, "Dispense order is abandoned or entered in error"
            ):
                future.result(timeout=5)

        self.assertFalse(MedicationDispense.objects.filter(order=self.order).exists())
        self.assert_stock(self.item, 500)
        self.assert_stock(self.other_item, 500)

    def test_reassignment_locks_both_orders_before_cancellation_reads_children(self):
        dispense = self.create_dispense()
        target = self.create_order()
        with ThreadPoolExecutor(max_workers=1) as executor:
            with transaction.atomic():
                self.reassign(dispense, target)
                for order in (self.order, target):
                    with self.subTest(order=order.pk):
                        future = executor.submit(
                            self.run_in_another_connection,
                            lambda order=order: self.cancel(order),
                        )
                        with self.assertRaises(ObjectLocked):
                            future.result(timeout=5)

            executor.submit(
                self.run_in_another_connection, lambda: self.cancel(self.order)
            ).result(timeout=5)
            dispense.refresh_from_db()
            self.assertEqual(dispense.order_id, target.pk)
            self.assertEqual(dispense.status, "completed")
            self.assert_stock(self.item, 400)

            executor.submit(
                self.run_in_another_connection, lambda: self.cancel(target)
            ).result(timeout=5)

        dispense.refresh_from_db()
        self.assertEqual(dispense.status, "cancelled")
        self.assert_stock(self.item, 500)

    def test_stale_update_rejects_changed_order_for_reassignment_and_omitted_order(
        self,
    ):
        remaining_stock = 500
        with ThreadPoolExecutor(max_workers=1) as executor:
            for reassign in (False, True):
                with self.subTest(reassign=reassign):
                    dispense = self.create_dispense()
                    remaining_stock -= 100
                    target = self.create_order()
                    data = {"status": "on_hold"}
                    if reassign:
                        data["order"] = str(self.create_order().external_id)
                    stale_instance = self.deserialize_update(
                        MedicationDispense.objects.get(pk=dispense.pk), **data
                    )
                    executor.submit(
                        self.run_in_another_connection,
                        lambda dispense=dispense, target=target: self.reassign(
                            dispense, target
                        ),
                    ).result(timeout=5)

                    with self.assertRaises(ObjectLocked):
                        self.view(MedicationDispenseViewSet).perform_update(
                            stale_instance
                        )

                    dispense.refresh_from_db()
                    self.assertEqual(dispense.order_id, target.pk)
                    self.assertEqual(dispense.status, "completed")
                    self.assert_stock(self.item, remaining_stock)
