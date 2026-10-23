from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier, Event, local
from types import SimpleNamespace
from unittest.mock import patch

from django.db import IntegrityError, close_old_connections, connections, transaction
from django.test import TransactionTestCase, skipUnlessDBFeature
from model_bakery import baker
from rest_framework.exceptions import ValidationError

from care.emr.api.viewsets.inventory.dispense_order import DispenseOrderViewSet
from care.emr.api.viewsets.inventory.supply_delivery import SupplyDeliveryViewSet
from care.emr.api.viewsets.medication_dispense import MedicationDispenseViewSet
from care.emr.locks.billing import InventoryItemLock
from care.emr.models.inventory_item import InventoryItem
from care.emr.models.medication_dispense import MedicationDispense
from care.emr.models.supply_delivery import SupplyDelivery
from care.emr.resources.inventory.inventory_item.create_inventory_item import (
    create_inventory_item,
)
from care.emr.resources.inventory.inventory_item.sync_inventory_item import (
    sync_inventory_item,
)
from care.emr.resources.invoice.return_items_invoice import cancel_return_invoice
from care.utils.lock import ObjectLocked


@skipUnlessDBFeature("has_select_for_update_nowait")
class InventoryLockFlowTests(TransactionTestCase):
    def setUp(self):
        self.user = baker.make("users.User")
        self.facility = baker.make("facility.Facility", created_by=self.user)
        self.origin = baker.make("emr.FacilityLocation", facility=self.facility)
        self.destination = baker.make("emr.FacilityLocation", facility=self.facility)
        knowledge = baker.make("emr.ProductKnowledge", facility=self.facility)
        self.product = baker.make(
            "emr.Product", facility=self.facility, product_knowledge=knowledge
        )
        self.origin_item = self.seed_stock(self.origin)
        self.destination_item = self.seed_stock(self.destination)
        self.transfer_order = baker.make(
            "emr.DeliveryOrder",
            origin=self.origin,
            destination=self.destination,
            status="in_progress",
        )
        self.patient = baker.make("emr.Patient")
        self.encounter = baker.make(
            "emr.Encounter", patient=self.patient, facility=self.facility
        )

    def seed_stock(self, location):
        item = baker.make(
            InventoryItem,
            location=location,
            product=self.product,
            net_content=500,
            status="active",
        )
        order = baker.make(
            "emr.DeliveryOrder", destination=location, status="in_progress"
        )
        baker.make(
            SupplyDelivery,
            order=order,
            supplied_item=self.product,
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

    def transfer(self, order=None, item=None):
        self.view(SupplyDeliveryViewSet).perform_create(
            SupplyDelivery(
                order=order or self.transfer_order,
                supplied_inventory_item=item or self.origin_item,
                supplied_item_quantity=100,
                status="in_progress",
                supplied_item_condition="normal",
                delivery_type="product",
            )
        )

    def dispense(self):
        instance = MedicationDispense(
            patient=self.patient,
            encounter=self.encounter,
            location=self.origin,
            item=self.origin_item,
            quantity=100,
            status="completed",
        )
        instance._fully_dispensed = None  # noqa: SLF001
        self.view(MedicationDispenseViewSet).perform_create(instance)

    def assert_stock(self, item, quantity):
        item.refresh_from_db()
        self.assertEqual(item.net_content, Decimal(quantity))
        sync_inventory_item(inventory_item=item)
        item.refresh_from_db()
        self.assertEqual(item.net_content, Decimal(quantity))

    def assert_conflict_then_retry(self, create, update, error=ObjectLocked):
        # Keep the first operation uncommitted after its recalculation, just as an
        # outer API/upsert transaction can. The other connection must not write
        # a stock total calculated without seeing that operation.
        with ThreadPoolExecutor(max_workers=1) as executor:
            with transaction.atomic():
                create()
                future = executor.submit(self.run_in_another_connection, update)
                with self.assertRaises(error):
                    future.result(timeout=5)
            executor.submit(self.run_in_another_connection, update).result(timeout=5)

    def test_supply_update_conflicts_with_uncommitted_transfer(self):
        order = baker.make(
            "emr.DeliveryOrder", destination=self.origin, status="in_progress"
        )
        incoming = baker.make(
            SupplyDelivery,
            order=order,
            supplied_item=self.product,
            supplied_inventory_item=self.origin_item,
            supplied_item_quantity=100,
            status="in_progress",
        )

        def update():
            instance = SupplyDelivery.objects.get(pk=incoming.pk)
            instance.status = "completed"
            self.view(SupplyDeliveryViewSet).perform_update(instance)

        self.assert_conflict_then_retry(self.transfer, update)
        self.assert_stock(self.origin_item, 500)

    def test_external_creation_conflicts_with_uncommitted_dispense(self):
        order = baker.make(
            "emr.DeliveryOrder", destination=self.origin, status="in_progress"
        )

        def incoming():
            self.view(SupplyDeliveryViewSet).perform_create(
                SupplyDelivery(
                    order=order,
                    supplied_item=self.product,
                    supplied_item_quantity=100,
                    status="completed",
                    supplied_item_condition="normal",
                    delivery_type="product",
                )
            )

        self.assert_conflict_then_retry(self.dispense, incoming, ValidationError)
        self.assertEqual(SupplyDelivery.objects.filter(order=order).count(), 1)
        self.assert_stock(self.origin_item, 500)

    def test_transfer_locks_destination_before_stock_is_written(self):
        reverse_order = baker.make(
            "emr.DeliveryOrder",
            origin=self.destination,
            destination=self.origin,
            status="in_progress",
        )

        def reverse_transfer():
            source = InventoryItem.objects.get(pk=self.destination_item.pk)
            self.transfer(reverse_order, source)

        self.assert_conflict_then_retry(
            self.dispense, reverse_transfer, ValidationError
        )
        self.assertEqual(SupplyDelivery.objects.filter(order=reverse_order).count(), 1)
        self.assert_stock(self.origin_item, 400)
        self.assert_stock(self.destination_item, 400)

    def test_dispense_cancel_conflicts_with_uncommitted_dispense(self):
        old = baker.make(
            MedicationDispense,
            patient=self.patient,
            encounter=self.encounter,
            location=self.origin,
            item=self.origin_item,
            quantity=100,
            status="completed",
        )
        sync_inventory_item(inventory_item=self.origin_item)

        def cancel():
            instance = MedicationDispense.objects.get(pk=old.pk)
            instance.status = "cancelled"
            instance._fully_dispensed = None  # noqa: SLF001
            self.view(MedicationDispenseViewSet).perform_update(instance)

        self.assert_conflict_then_retry(self.dispense, cancel)
        self.assert_stock(self.origin_item, 400)

    def test_order_cancel_conflicts_with_uncommitted_dispense(self):
        order = baker.make(
            "emr.DispenseOrder",
            patient=self.patient,
            facility=self.facility,
            location=self.origin,
            status="completed",
        )
        baker.make(
            MedicationDispense,
            patient=self.patient,
            encounter=self.encounter,
            location=self.origin,
            item=self.origin_item,
            quantity=100,
            status="completed",
            order=order,
        )
        sync_inventory_item(inventory_item=self.origin_item)

        def cancel():
            instance = type(order).objects.get(pk=order.pk)
            instance.status = "abandoned"
            self.view(DispenseOrderViewSet).perform_update(instance)

        self.assert_conflict_then_retry(self.dispense, cancel)
        self.assert_stock(self.origin_item, 400)

    def test_opposing_transfers_with_prior_locks_do_not_deadlock(self):
        reverse_order = baker.make(
            "emr.DeliveryOrder",
            origin=self.destination,
            destination=self.origin,
            status="in_progress",
        )
        barrier = Barrier(2)

        def transfer_with_prior_lock(order, item_id):
            try:
                with transaction.atomic():
                    item = InventoryItem.objects.get(pk=item_id)
                    with InventoryItemLock(item):
                        # Earlier operations in an upsert can already hold a row.
                        barrier.wait(timeout=5)
                        self.transfer(order, item)
                return True
            except ValidationError:
                return False

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(
                    self.run_in_another_connection,
                    lambda: transfer_with_prior_lock(
                        self.transfer_order, self.origin_item.pk
                    ),
                ),
                executor.submit(
                    self.run_in_another_connection,
                    lambda: transfer_with_prior_lock(
                        reverse_order, self.destination_item.pk
                    ),
                ),
            ]
            results = [future.result(timeout=10) for future in futures]
        self.assertFalse(all(results))
        self.assertEqual(
            SupplyDelivery.objects.filter(order__origin__isnull=False).count(),
            sum(results),
        )
        self.assert_stock(self.origin_item, 400 if results[0] else 500)
        self.assert_stock(self.destination_item, 400 if results[1] else 500)

    def test_sync_itself_rejects_locked_stock(self):
        def sync():
            sync_inventory_item(location=self.origin, product=self.product)

        self.assert_conflict_then_retry(self.dispense, sync)
        self.assert_stock(self.origin_item, 400)

    def test_return_cancellation_conflicts_and_can_retry(self):
        order = baker.make(
            "emr.DeliveryOrder", destination=self.origin, status="in_progress"
        )
        for _ in range(2):
            baker.make(
                SupplyDelivery,
                order=order,
                supplied_item=self.product,
                supplied_inventory_item=self.origin_item,
                supplied_item_quantity=100,
                status="completed",
            )
        sync_inventory_item(inventory_item=self.origin_item)

        def cancel():
            cancel_return_invoice(order)

        self.assert_conflict_then_retry(self.dispense, cancel)
        self.assert_stock(self.origin_item, 400)
        self.assertEqual(
            SupplyDelivery.objects.filter(
                order=order, status="entered_in_error"
            ).count(),
            2,
        )

    def assert_first_creation_serialized(self, operation, location):
        first_created = Event()
        second_processed = Event()
        first_finished = Event()
        context = local()
        original_save = InventoryItem.save

        def save(item, *args, **kwargs):
            creating_destination = not item.pk and item.location_id == location.pk
            result = original_save(item, *args, **kwargs)
            if creating_destination:
                if context.role == "first":
                    first_created.set()
                    self.assertTrue(second_processed.wait(timeout=10))
                else:
                    # Reproduce the original race: a second insert must not
                    # commit a different PK once the first request finishes.
                    second_processed.set()
                    self.assertTrue(first_finished.wait(timeout=10))
            return result

        def create(role):
            context.role = role
            try:
                operation()
                return True
            except ValidationError:
                return False
            finally:
                if role == "first":
                    first_finished.set()
                else:
                    second_processed.set()

        with (
            patch.object(InventoryItem, "save", save),
            ThreadPoolExecutor(max_workers=2) as executor,
        ):
            first = executor.submit(
                self.run_in_another_connection, lambda: create("first")
            )
            self.assertTrue(first_created.wait(timeout=5))
            second = executor.submit(
                self.run_in_another_connection, lambda: create("second")
            )
            self.assertTrue(first.result(timeout=15))
            self.assertFalse(second.result(timeout=15))
        operation()
        self.assertEqual(
            InventoryItem.objects.filter(
                product=self.product, location=location
            ).count(),
            1,
        )

    def test_first_external_deliveries_share_one_inventory_row(self):
        location = baker.make("emr.FacilityLocation", facility=self.facility)
        order = baker.make(
            "emr.DeliveryOrder", destination=location, status="in_progress"
        )

        def receive():
            self.view(SupplyDeliveryViewSet).perform_create(
                SupplyDelivery(
                    order=order,
                    supplied_item=self.product,
                    supplied_item_quantity=100,
                    status="completed",
                    supplied_item_condition="normal",
                    delivery_type="product",
                )
            )

        self.assert_first_creation_serialized(receive, location)
        self.assertEqual(SupplyDelivery.objects.filter(order=order).count(), 2)
        item = InventoryItem.objects.get(product=self.product, location=location)
        self.assert_stock(item, 200)

    def test_first_transfers_share_one_destination_inventory_row(self):
        location = baker.make("emr.FacilityLocation", facility=self.facility)
        order = baker.make(
            "emr.DeliveryOrder",
            origin=self.origin,
            destination=location,
            status="in_progress",
        )

        def transfer():
            source = InventoryItem.objects.get(pk=self.origin_item.pk)
            self.transfer(order, source)

        self.assert_first_creation_serialized(transfer, location)
        for instance in SupplyDelivery.objects.filter(order=order):
            instance.status = "completed"
            self.view(SupplyDeliveryViewSet).perform_update(instance)
        item = InventoryItem.objects.get(product=self.product, location=location)
        self.assert_stock(item, 200)
        self.assert_stock(self.origin_item, 300)

    def test_creation_lock_is_released_on_outer_rollback(self):
        location = baker.make("emr.FacilityLocation", facility=self.facility)
        with self.assertRaisesMessage(ValueError, "rollback"), transaction.atomic():
            create_inventory_item(self.product, location)
            raise ValueError("rollback")
        with ThreadPoolExecutor(max_workers=1) as executor:
            item = executor.submit(
                self.run_in_another_connection,
                lambda: create_inventory_item(self.product, location),
            ).result(timeout=5)
        self.assertEqual(
            InventoryItem.objects.get(product=self.product, location=location).pk,
            item.pk,
        )

    def test_creation_does_not_block_receipts_into_existing_stock(self):
        location = baker.make("emr.FacilityLocation", facility=self.facility)
        order = baker.make(
            "emr.DeliveryOrder", destination=self.destination, status="in_progress"
        )

        def receive():
            self.view(SupplyDeliveryViewSet).perform_create(
                SupplyDelivery(
                    order=order,
                    supplied_item=self.product,
                    supplied_item_quantity=100,
                    status="completed",
                    supplied_item_condition="normal",
                    delivery_type="product",
                )
            )

        with ThreadPoolExecutor(max_workers=1) as executor, transaction.atomic():
            create_inventory_item(self.product, location)
            executor.submit(self.run_in_another_connection, receive).result(timeout=5)
        self.assert_stock(self.destination_item, 600)

    def test_database_rejects_a_duplicate_active_inventory_row(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            baker.make(
                InventoryItem,
                product=self.product,
                location=self.origin,
                status="active",
            )
        self.origin_item.delete()
        replacement = create_inventory_item(self.product, self.origin)
        self.assertNotEqual(replacement.pk, self.origin_item.pk)

    def test_stale_update_cannot_reactivate_a_cancelled_dispense(self):
        self.dispense()
        stale = MedicationDispense.objects.get(item=self.origin_item)
        self.view(MedicationDispenseViewSet).validate_data(None, stale)

        def cancel_then_consume_stock():
            current = MedicationDispense.objects.get(pk=stale.pk)
            current.status = "cancelled"
            current._fully_dispensed = None  # noqa: SLF001
            self.view(MedicationDispenseViewSet).perform_update(current)
            instance = MedicationDispense(
                patient=self.patient,
                encounter=self.encounter,
                location=self.origin,
                item=InventoryItem.objects.get(pk=self.origin_item.pk),
                quantity=500,
                status="completed",
            )
            instance._fully_dispensed = None  # noqa: SLF001
            self.view(MedicationDispenseViewSet).perform_create(instance)

        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(
                self.run_in_another_connection, cancel_then_consume_stock
            ).result(timeout=5)
        stale.status = "completed"
        stale._fully_dispensed = None  # noqa: SLF001
        with self.assertRaisesMessage(
            ValidationError, "No updates allowed on cancelled medication dispense"
        ):
            self.view(MedicationDispenseViewSet).perform_update(stale)
        stale.refresh_from_db()
        self.assertEqual(stale.status, "cancelled")
        self.assert_stock(self.origin_item, 0)
