from datetime import UTC, datetime, timedelta

from care.emr.models import SchedulableResource, Schedule
from care.emr.models.activity_definition import ActivityDefinition
from care.emr.models.charge_item_definition import ChargeItemDefinition
from care.emr.models.product import Product
from care.emr.resources.scheduling.schedule.spec import SchedulableResourceTypeOptions
from care.utils.tests.base import CareAPITestBase


class TestChargeItemDefinitionSignals(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)

    def create_charge_item_definition(self, **kwargs):
        data = {
            "facility": self.facility,
            "status": "active",
            "title": self.fake.sentence(nb_words=4),
            "slug": f"f-{self.facility.external_id}-{self.fake.slug()}",
        }
        data.update(**kwargs)
        return ChargeItemDefinition.objects.create(**data)

    def create_product(self, charge_item_definition=None, **kwargs):
        from model_bakery import baker

        product_knowledge = baker.make("emr.ProductKnowledge", facility=self.facility)
        data = {
            "facility": self.facility,
            "product_knowledge": product_knowledge,
            "charge_item_definition": charge_item_definition,
            "status": "active",
            "product_type": "medication",
        }
        data.update(**kwargs)
        return Product.objects.create(**data)

    def create_schedule(
        self, charge_item_definition=None, revisit_charge_item_definition=None, **kwargs
    ):
        resource = SchedulableResource.objects.create(
            resource_type=SchedulableResourceTypeOptions.practitioner.value,
            user=self.user,
            facility=self.facility,
        )
        data = {
            "resource": resource,
            "name": "Test Schedule",
            "valid_from": datetime.now(UTC),
            "valid_to": datetime.now(UTC) + timedelta(days=30),
            "charge_item_definition": charge_item_definition,
            "revisit_charge_item_definition": revisit_charge_item_definition,
        }
        data.update(**kwargs)
        return Schedule.objects.create(**data)

    def create_activity_definition(self, charge_item_definitions=None, **kwargs):
        data = {
            "facility": self.facility,
            "slug": f"f-{self.facility.external_id}-{self.fake.slug()}",
            "title": self.fake.sentence(nb_words=4),
            "classification": "test",
            "status": "active",
            "description": self.fake.text(),
            "usage": self.fake.text(),
            "kind": "ServiceRequest",
            "charge_item_definitions": charge_item_definitions or [],
        }
        data.update(**kwargs)
        return ActivityDefinition.objects.create(**data)

    # Product Signal Tests

    def test_product_link_sets_separately_billable_false(self):
        charge_item_def = self.create_charge_item_definition()
        self.assertTrue(charge_item_def.separately_billable)

        self.create_product(charge_item_definition=charge_item_def)

        charge_item_def.refresh_from_db()
        self.assertFalse(charge_item_def.separately_billable)

    def test_product_unlink_recalculates_separately_billable(self):
        charge_item_def = self.create_charge_item_definition()
        product = self.create_product(charge_item_definition=charge_item_def)

        charge_item_def.refresh_from_db()
        self.assertFalse(charge_item_def.separately_billable)

        product.charge_item_definition = None
        product.save()

        charge_item_def.refresh_from_db()
        self.assertTrue(charge_item_def.separately_billable)

    def test_product_delete_recalculates_separately_billable(self):
        charge_item_def = self.create_charge_item_definition()
        product = self.create_product(charge_item_definition=charge_item_def)

        charge_item_def.refresh_from_db()
        self.assertFalse(charge_item_def.separately_billable)

        product.delete()

        charge_item_def.refresh_from_db()
        self.assertTrue(charge_item_def.separately_billable)

    def test_product_change_link_recalculates_old_and_sets_new(self):
        charge_item_def_1 = self.create_charge_item_definition()
        charge_item_def_2 = self.create_charge_item_definition()
        product = self.create_product(charge_item_definition=charge_item_def_1)

        charge_item_def_1.refresh_from_db()
        self.assertFalse(charge_item_def_1.separately_billable)

        product.charge_item_definition = charge_item_def_2
        product.save()

        charge_item_def_1.refresh_from_db()
        charge_item_def_2.refresh_from_db()
        self.assertTrue(charge_item_def_1.separately_billable)
        self.assertFalse(charge_item_def_2.separately_billable)

    # Schedule Signal Tests

    def test_schedule_link_sets_separately_billable_false(self):
        charge_item_def = self.create_charge_item_definition()
        self.assertTrue(charge_item_def.separately_billable)

        self.create_schedule(charge_item_definition=charge_item_def)

        charge_item_def.refresh_from_db()
        self.assertFalse(charge_item_def.separately_billable)

    def test_schedule_revisit_link_sets_separately_billable_false(self):
        charge_item_def = self.create_charge_item_definition()
        self.assertTrue(charge_item_def.separately_billable)

        self.create_schedule(revisit_charge_item_definition=charge_item_def)

        charge_item_def.refresh_from_db()
        self.assertFalse(charge_item_def.separately_billable)

    def test_schedule_unlink_recalculates_separately_billable(self):
        charge_item_def = self.create_charge_item_definition()
        schedule = self.create_schedule(charge_item_definition=charge_item_def)

        charge_item_def.refresh_from_db()
        self.assertFalse(charge_item_def.separately_billable)

        schedule.charge_item_definition = None
        schedule.save()

        charge_item_def.refresh_from_db()
        self.assertTrue(charge_item_def.separately_billable)

    def test_schedule_delete_recalculates_separately_billable(self):
        charge_item_def = self.create_charge_item_definition()
        schedule = self.create_schedule(charge_item_definition=charge_item_def)

        charge_item_def.refresh_from_db()
        self.assertFalse(charge_item_def.separately_billable)

        schedule.delete()

        charge_item_def.refresh_from_db()
        self.assertTrue(charge_item_def.separately_billable)

    # ActivityDefinition Signal Tests

    def test_activity_definition_link_sets_separately_billable_false(self):
        charge_item_def = self.create_charge_item_definition()
        self.assertTrue(charge_item_def.separately_billable)

        self.create_activity_definition(charge_item_definitions=[charge_item_def.id])

        charge_item_def.refresh_from_db()
        self.assertFalse(charge_item_def.separately_billable)

    def test_activity_definition_unlink_recalculates_separately_billable(self):
        charge_item_def = self.create_charge_item_definition()
        activity_def = self.create_activity_definition(
            charge_item_definitions=[charge_item_def.id]
        )

        charge_item_def.refresh_from_db()
        self.assertFalse(charge_item_def.separately_billable)

        activity_def.charge_item_definitions = []
        activity_def.save()

        charge_item_def.refresh_from_db()
        self.assertTrue(charge_item_def.separately_billable)

    def test_activity_definition_delete_recalculates_separately_billable(self):
        charge_item_def = self.create_charge_item_definition()
        activity_def = self.create_activity_definition(
            charge_item_definitions=[charge_item_def.id]
        )

        charge_item_def.refresh_from_db()
        self.assertFalse(charge_item_def.separately_billable)

        activity_def.delete()

        charge_item_def.refresh_from_db()
        self.assertTrue(charge_item_def.separately_billable)

    def test_activity_definition_add_multiple_charge_items(self):
        charge_item_def_1 = self.create_charge_item_definition()
        charge_item_def_2 = self.create_charge_item_definition()

        self.create_activity_definition(
            charge_item_definitions=[charge_item_def_1.id, charge_item_def_2.id]
        )

        charge_item_def_1.refresh_from_db()
        charge_item_def_2.refresh_from_db()
        self.assertFalse(charge_item_def_1.separately_billable)
        self.assertFalse(charge_item_def_2.separately_billable)

    def test_activity_definition_partial_unlink(self):
        charge_item_def_1 = self.create_charge_item_definition()
        charge_item_def_2 = self.create_charge_item_definition()
        activity_def = self.create_activity_definition(
            charge_item_definitions=[charge_item_def_1.id, charge_item_def_2.id]
        )

        activity_def.charge_item_definitions = [charge_item_def_1.id]
        activity_def.save()

        charge_item_def_1.refresh_from_db()
        charge_item_def_2.refresh_from_db()
        self.assertFalse(charge_item_def_1.separately_billable)
        self.assertTrue(charge_item_def_2.separately_billable)

    # Cross-model Tests

    def test_unlink_keeps_false_if_linked_elsewhere(self):
        charge_item_def = self.create_charge_item_definition()
        product = self.create_product(charge_item_definition=charge_item_def)
        self.create_schedule(charge_item_definition=charge_item_def)

        charge_item_def.refresh_from_db()
        self.assertFalse(charge_item_def.separately_billable)

        product.charge_item_definition = None
        product.save()

        charge_item_def.refresh_from_db()
        self.assertFalse(charge_item_def.separately_billable)

    def test_multiple_links_all_removed(self):
        charge_item_def = self.create_charge_item_definition()
        product = self.create_product(charge_item_definition=charge_item_def)
        schedule = self.create_schedule(charge_item_definition=charge_item_def)
        activity_def = self.create_activity_definition(
            charge_item_definitions=[charge_item_def.id]
        )

        charge_item_def.refresh_from_db()
        self.assertFalse(charge_item_def.separately_billable)

        product.charge_item_definition = None
        product.save()
        charge_item_def.refresh_from_db()
        self.assertFalse(charge_item_def.separately_billable)

        schedule.charge_item_definition = None
        schedule.save()
        charge_item_def.refresh_from_db()
        self.assertFalse(charge_item_def.separately_billable)

        activity_def.charge_item_definitions = []
        activity_def.save()
        charge_item_def.refresh_from_db()
        self.assertTrue(charge_item_def.separately_billable)
