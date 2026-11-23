from decimal import Decimal

from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from model_bakery import baker

from care.emr.models.inventory_item import InventoryItem
from care.emr.models.location import FacilityLocation


class InventoryItemUniquenessMigrationTests(TransactionTestCase):
    migrate_from = [("emr", "0082_remove_encounter_encounter_class_history")]
    migrate_to = [
        ("emr", "0083_inventoryitem_unique_active_inventory_product_location")
    ]

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        self.latest_migrations = executor.loader.graph.leaf_nodes()
        self.addCleanup(self.restore_schema)
        executor.migrate(self.migrate_from)
        executor = MigrationExecutor(connection)
        self.old_apps = executor.loader.project_state(
            [
                node
                for node in executor.loader.applied_migrations
                if node in executor.loader.graph.nodes
            ]
        ).apps
        self.location_model = self.old_apps.get_model("emr", "FacilityLocation")
        self.inventory_model = self.old_apps.get_model("emr", "InventoryItem")
        self.delivery_model = self.old_apps.get_model("emr", "SupplyDelivery")
        self.dispense_model = self.old_apps.get_model("emr", "MedicationDispense")
        self.order_model = self.old_apps.get_model("emr", "DeliveryOrder")
        self.facility = baker.make(
            self.old_apps.get_model("facility", "Facility"),
            created_by=baker.make(self.old_apps.get_model("users", "User")),
        )

    def restore_schema(self):
        MigrationExecutor(connection).migrate(self.latest_migrations)

    def test_duplicates_are_consolidated_before_enforcing_uniqueness(self):
        location = baker.make(self.location_model, facility_id=self.facility.pk)
        destination = baker.make(self.location_model, facility_id=self.facility.pk)
        knowledge = baker.make(
            self.old_apps.get_model("emr", "ProductKnowledge"), facility=self.facility
        )
        product = baker.make(
            self.old_apps.get_model("emr", "Product"),
            facility=self.facility,
            product_knowledge=knowledge,
        )
        first = baker.make(
            self.inventory_model,
            product=product,
            location_id=location.pk,
            net_content=123,
        )
        duplicate = baker.make(
            self.inventory_model,
            product=product,
            location_id=location.pk,
            net_content=200,
        )
        extra_duplicate = baker.make(
            self.inventory_model,
            product=product,
            location_id=location.pk,
            net_content=300,
        )
        unrelated = baker.make(
            self.inventory_model,
            product=product,
            location_id=destination.pk,
            net_content=777,
        )
        previously_deleted = baker.make(
            self.inventory_model,
            product=product,
            location_id=location.pk,
            net_content=666,
            deleted=True,
        )
        incoming_order = baker.make(self.order_model, destination_id=location.pk)
        for item in (first, duplicate):
            baker.make(
                self.delivery_model,
                order=incoming_order,
                supplied_item=product,
                supplied_inventory_item=item,
                supplied_item_quantity=100,
                status="completed",
            )
        outgoing_order = baker.make(
            self.order_model, origin_id=location.pk, destination_id=destination.pk
        )
        outgoing = baker.make(
            self.delivery_model,
            order=outgoing_order,
            supplied_inventory_item=duplicate,
            supplied_item_quantity=40,
            status="in_progress",
        )
        patient = baker.make(self.old_apps.get_model("emr", "Patient"))
        encounter = baker.make(
            self.old_apps.get_model("emr", "Encounter"),
            patient=patient,
            facility=self.facility,
        )
        dispense = baker.make(
            self.dispense_model,
            item=duplicate,
            quantity=60,
            status="completed",
            location_id=location.pk,
            encounter=encounter,
            patient=patient,
        )
        cancelled_dispense = baker.make(
            self.dispense_model,
            item=extra_duplicate,
            quantity=999,
            status="cancelled",
            location_id=location.pk,
            encounter=encounter,
            patient=patient,
        )
        deleted_delivery = baker.make(
            self.delivery_model,
            order=incoming_order,
            supplied_inventory_item=duplicate,
            supplied_item_quantity=999,
            status="completed",
            deleted=True,
        )
        deleted_dispense = baker.make(
            self.dispense_model,
            item=extra_duplicate,
            quantity=999,
            status="completed",
            location_id=location.pk,
            encounter=encounter,
            patient=patient,
            deleted=True,
        )
        all_deliveries = self.delivery_model._base_manager.all()  # noqa: SLF001
        all_dispenses = self.dispense_model._base_manager.all()  # noqa: SLF001
        delivery_ids = list(all_deliveries.order_by("pk").values_list("pk", flat=True))
        dispense_ids = list(all_dispenses.order_by("pk").values_list("pk", flat=True))

        MigrationExecutor(connection).migrate(self.migrate_to)
        self.restore_schema()

        self.assertEqual(
            FacilityLocation.objects.get(pk=location.pk).inventory_usage, "none"
        )
        first.refresh_from_db()
        previously_deleted.refresh_from_db()
        unrelated.refresh_from_db()
        outgoing.refresh_from_db()
        dispense.refresh_from_db()
        cancelled_dispense.refresh_from_db()
        deleted_delivery.refresh_from_db()
        deleted_dispense.refresh_from_db()
        self.assertEqual(first.net_content, Decimal(123))
        self.assertFalse(
            InventoryItem._base_manager.filter(  # noqa: SLF001
                pk__in=[duplicate.pk, extra_duplicate.pk]
            ).exists()
        )
        self.assertEqual(previously_deleted.net_content, Decimal(666))
        self.assertEqual(unrelated.net_content, Decimal(777))
        self.assertEqual(outgoing.supplied_inventory_item_id, first.pk)
        self.assertEqual(dispense.item_id, first.pk)
        self.assertEqual(cancelled_dispense.item_id, first.pk)
        self.assertEqual(deleted_delivery.supplied_inventory_item_id, first.pk)
        self.assertEqual(deleted_dispense.item_id, first.pk)
        self.assertTrue(deleted_delivery.deleted)
        self.assertTrue(deleted_dispense.deleted)
        self.assertEqual(
            list(all_deliveries.order_by("pk").values_list("pk", flat=True)),
            delivery_ids,
        )
        self.assertEqual(
            list(all_dispenses.order_by("pk").values_list("pk", flat=True)),
            dispense_ids,
        )
        self.assertEqual(
            InventoryItem.objects.filter(
                product_id=product.pk, location_id=location.pk
            ).count(),
            1,
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            baker.make(self.inventory_model, product=product, location_id=location.pk)
