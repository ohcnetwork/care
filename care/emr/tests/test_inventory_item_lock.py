from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Event

from django.db import close_old_connections, connections, transaction
from django.test import TransactionTestCase, skipUnlessDBFeature
from model_bakery import baker

from care.emr.locks.billing import InventoryItemLock, lock_inventory_items
from care.emr.models.inventory_item import InventoryItem
from care.utils.lock import ObjectLocked


class InventoryItemLockTests(TransactionTestCase):
    def setUp(self):
        user = baker.make("users.User")
        facility = baker.make("facility.Facility", created_by=user)
        location = baker.make("emr.FacilityLocation", facility=facility)
        knowledge = baker.make("emr.ProductKnowledge", facility=facility)
        product = baker.make(
            "emr.Product", facility=facility, product_knowledge=knowledge
        )
        self.item = baker.make(
            InventoryItem, location=location, product=product, net_content=Decimal(500)
        )

    def read_stock_in_another_connection(self):
        close_old_connections()
        try:
            item = InventoryItem.objects.get(pk=self.item.pk)
            with InventoryItemLock(item):
                return item.net_content
        finally:
            connections["default"].close()

    def test_repeated_locks_refresh_stock_in_the_same_transaction(self):
        stale = InventoryItem.objects.get(pk=self.item.pk)
        lock = InventoryItemLock(self.item)
        with transaction.atomic(), lock:
            self.item.net_content = Decimal(400)
            self.item.save(update_fields=["net_content"])
            with lock, lock_inventory_items([stale, stale]):
                self.assertEqual(stale.net_content, Decimal(400))
        self.item.refresh_from_db()
        self.assertEqual(self.item.net_content, Decimal(400))

    @skipUnlessDBFeature("has_select_for_update_nowait")
    def test_concurrent_connection_is_rejected_until_commit(self):
        with ThreadPoolExecutor(max_workers=1) as executor:
            with InventoryItemLock(self.item):
                self.item.net_content = Decimal(400)
                self.item.save(update_fields=["net_content"])
                future = executor.submit(self.read_stock_in_another_connection)
                with self.assertRaises(ObjectLocked):
                    future.result(timeout=5)
            future = executor.submit(self.read_stock_in_another_connection)
            self.assertEqual(future.result(timeout=5), Decimal(400))

    @skipUnlessDBFeature("has_select_for_update_nowait")
    def test_outer_rollback_releases_the_lock(self):
        with self.assertRaisesMessage(ValueError, "rollback"), transaction.atomic():
            with InventoryItemLock(self.item):
                self.item.net_content = Decimal(400)
                self.item.save(update_fields=["net_content"])
            raise ValueError("rollback")
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.read_stock_in_another_connection)
            self.assertEqual(future.result(timeout=5), Decimal(500))

    @skipUnlessDBFeature("has_select_for_update_nowait")
    def test_failed_batch_releases_previously_acquired_rows(self):
        second = baker.make(
            InventoryItem,
            location=baker.make(
                "emr.FacilityLocation", facility=self.item.location.facility
            ),
            product=self.item.product,
        )
        acquired = Event()
        release = Event()

        def hold_second_row():
            close_old_connections()
            try:
                item = InventoryItem.objects.get(pk=second.pk)
                with InventoryItemLock(item):
                    acquired.set()
                    self.assertTrue(release.wait(timeout=10))
            finally:
                connections["default"].close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            holder = executor.submit(hold_second_row)
            try:
                self.assertTrue(acquired.wait(timeout=5))
                with transaction.atomic():
                    with (
                        self.assertRaises(ObjectLocked),
                        lock_inventory_items([second, self.item, self.item]),
                    ):
                        pass
                    future = executor.submit(self.read_stock_in_another_connection)
                    self.assertEqual(future.result(timeout=5), Decimal(500))
            finally:
                release.set()
                holder.result(timeout=5)
