from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from model_bakery import baker

from care.emr.api.viewsets.charge_item import ChargeItemViewSet
from care.emr.models.charge_item import ChargeItem
from care.emr.models.invoice import Invoice
from care.emr.models.resource_category import ResourceCategory
from care.emr.resources.charge_item.queryset import charge_items_for_serialization
from care.emr.resources.charge_item.spec import ChargeItemReadSpec
from care.emr.resources.invoice.spec import InvoiceRetrieveSpec
from care.emr.resources.invoice.sync_items import sync_invoice_items


@override_settings(
    ACCOUNTING_PRECISION=2,
    ACCOUNTING_ROUNDING_METHOD="care.utils.rounding.RoundingHalfUp",
    INVOICE_FINAL_AMOUNT_PRECISION=2,
    INVOICE_FINAL_AMOUNT_ROUNDING_METHOD="care.utils.rounding.RoundingHalfUp",
)
class ChargeItemSerializationQueriesTests(TestCase):
    def setUp(self):
        self.user = baker.make("users.User")
        self.facility = baker.make("facility.Facility", created_by=self.user)
        self.patient = baker.make("emr.Patient")
        self.account = baker.make(
            "emr.Account",
            facility=self.facility,
            patient=self.patient,
            status="active",
            billing_status="open",
        )
        category = baker.make(
            "emr.ResourceCategory",
            facility=self.facility,
            resource_type="charge_item_definition",
            slug=f"f-{self.facility.external_id}-consultations",
        )
        self.definition = baker.make(
            "emr.ChargeItemDefinition",
            facility=self.facility,
            category=category,
            status="active",
            title="Consultation",
            slug=f"f-{self.facility.external_id}-consultation",
        )
        # Existing invoice snapshots can be large before another item is attached.
        self.snapshot = [{"note": "x" * 2048} for _ in range(64)]
        self.invoice = baker.make(
            Invoice,
            facility=self.facility,
            patient=self.patient,
            account=self.account,
            title="Draft consultation invoice",
            status="draft",
            total_net=Decimal("123.00"),
            total_gross=Decimal("135.00"),
            charge_items_copy=self.snapshot,
        )
        # Keep these query budgets independent of the external user cache while
        # still detecting an accidental database fetch of performer_actor.
        self.actor_cache = patch(
            "care.emr.resources.charge_item.spec.model_from_cache",
            return_value={"id": str(self.user.external_id)},
        )
        self.actor_cache.start()
        self.addCleanup(self.actor_cache.stop)

    def add_charge_items(self, count):
        components = [
            {"monetary_component_type": "base", "amount": "100.00"},
            {"monetary_component_type": "surcharge", "amount": "10.00"},
            {"monetary_component_type": "discount", "amount": "5.00"},
            {"monetary_component_type": "tax", "amount": "10.50"},
        ]
        items = baker.make(
            ChargeItem,
            facility=self.facility,
            patient=self.patient,
            account=self.account,
            paid_invoice=self.invoice,
            charge_item_definition=self.definition,
            performer_actor=self.user,
            title="Consultation",
            status="billed",
            quantity=Decimal(1),
            unit_price_components=components,
            total_price_components=components,
            total_price=Decimal("115.50"),
            _quantity=count,
        )
        self.invoice.charge_items.extend(item.pk for item in items)
        self.invoice.save(update_fields=["charge_items"])

    def assert_no_invoice_snapshot_selected(self, queries):
        for query in queries:
            self.assertNotIn('"charge_items_copy"', query["sql"])

    def test_shared_invoice_is_loaded_once_without_its_snapshot(self):
        for count in (1, 12):
            with self.subTest(count=count):
                self.add_charge_items(count - len(self.invoice.charge_items))
                with CaptureQueriesContext(connection) as queries:
                    items = list(
                        charge_items_for_serialization(
                            ChargeItem.objects.filter(paid_invoice=self.invoice)
                        )
                    )
                    serialized = [
                        ChargeItemReadSpec.serialize(item).to_json() for item in items
                    ]

                self.assertEqual(len(queries), 3)
                self.assertEqual(len(serialized), count)
                self.assert_no_invoice_snapshot_selected(queries)
                self.assertTrue(
                    all(item.paid_invoice is items[0].paid_invoice for item in items)
                )
                self.assertIn(
                    "charge_items_copy", items[0].paid_invoice.get_deferred_fields()
                )
                self.assertEqual(
                    serialized[0]["charge_item_definition"]["category"]["id"],
                    str(self.definition.category.external_id),
                )
                self.assertEqual(
                    serialized[0]["performer_actor"]["id"], str(self.user.external_id)
                )

    def test_invoice_sync_queries_remain_bounded_and_preserve_snapshot_values(self):
        for count in (1, 12):
            with self.subTest(count=count):
                self.add_charge_items(count - len(self.invoice.charge_items))
                with CaptureQueriesContext(connection) as queries:
                    sync_invoice_items(self.invoice)

                self.assertEqual(len(queries), 3)
                self.assert_no_invoice_snapshot_selected(queries)
                self.assertEqual(self.invoice.total_net, Decimal("105.00") * count)
                self.assertEqual(self.invoice.total_gross, Decimal("115.50") * count)
                self.assertEqual(len(self.invoice.charge_items_copy), count)
                for item in self.invoice.charge_items_copy:
                    self.assertEqual(
                        item["paid_invoice"]["id"], str(self.invoice.external_id)
                    )
                    self.assertEqual(item["paid_invoice"]["title"], self.invoice.title)
                    # Embedded invoice values have always reflected its saved
                    # state before recalculation; eager loading must preserve it.
                    self.assertEqual(
                        Decimal(item["paid_invoice"]["total_net"]), Decimal("123.00")
                    )

    def test_draft_invoice_serialization_queries_remain_bounded(self):
        for count in (1, 12):
            with self.subTest(count=count):
                self.add_charge_items(count - len(self.invoice.charge_items))
                invoice = Invoice.objects.select_related("account__patient").get(
                    pk=self.invoice.pk
                )
                with CaptureQueriesContext(connection) as queries:
                    data = InvoiceRetrieveSpec.serialize(invoice).to_json()

                self.assertEqual(len(queries), 4)
                self.assert_no_invoice_snapshot_selected(queries)
                self.assertEqual(len(data["charge_items"]), count)
                self.assertEqual(
                    data["charge_items"][0]["paid_invoice"]["id"],
                    str(self.invoice.external_id),
                )
                self.assertEqual(invoice.charge_items_copy, self.snapshot)

    def test_charge_item_viewset_serialization_queries_remain_bounded(self):
        view = ChargeItemViewSet()
        view.request = SimpleNamespace(user=self.user)
        with (
            patch.object(view, "get_facility_obj", return_value=self.facility),
            patch(
                "care.emr.api.viewsets.charge_item.AuthorizationController.call",
                return_value=True,
            ),
        ):
            for count in (1, 12):
                with self.subTest(count=count):
                    self.add_charge_items(count - len(self.invoice.charge_items))
                    with CaptureQueriesContext(connection) as queries:
                        data = [
                            view.serialize_list(item) for item in view.get_queryset()
                        ]

                    self.assertEqual(len(queries), 3)
                    self.assert_no_invoice_snapshot_selected(queries)
                    self.assertEqual(len(data), count)
                    self.assertEqual(
                        data[0]["paid_invoice"]["account"]["id"],
                        str(self.account.external_id),
                    )

    def test_shared_category_refreshes_its_missing_parent_cache_once(self):
        parent = baker.make(
            ResourceCategory,
            facility=self.facility,
            resource_type="charge_item_definition",
            slug=f"f-{self.facility.external_id}-services",
        )
        query_counts = []
        for count in (1, 12):
            with self.subTest(count=count):
                ResourceCategory.objects.filter(pk=self.definition.category_id).update(
                    parent=parent, cached_parent_json={}
                )
                self.add_charge_items(count - len(self.invoice.charge_items))
                items = list(
                    charge_items_for_serialization(
                        ChargeItem.objects.filter(paid_invoice=self.invoice)
                    )
                )
                self.assertTrue(
                    all(
                        item.charge_item_definition.category
                        is items[0].charge_item_definition.category
                        for item in items
                    )
                )

                with CaptureQueriesContext(connection) as queries:
                    data = [
                        ChargeItemReadSpec.serialize(item).to_json() for item in items
                    ]

                # Fetch the parent and refresh the child's cache once, regardless
                # of how many items share the category. Saving also uses savepoints.
                self.assertEqual(
                    sum(query["sql"].startswith("SELECT") for query in queries), 1
                )
                self.assertEqual(
                    sum(query["sql"].startswith("UPDATE") for query in queries), 1
                )
                query_counts.append(len(queries))
                self.assertTrue(
                    all(
                        item["charge_item_definition"]["category"]["parent"]["id"]
                        == str(parent.external_id)
                        for item in data
                    )
                )

        self.assertEqual(query_counts[0], query_counts[1])
