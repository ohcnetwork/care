from importlib import import_module

from django.db import connection
from django.db.migrations.loader import MigrationLoader
from model_bakery import baker

from care.emr.models.location import FacilityLocation
from care.utils.tests.base import CareAPITestBase


class LocationChildFlagsBackfillTests(CareAPITestBase):
    migration = "0101_facilitylocation_child_flags"

    def setUp(self):
        super().setUp()
        self.facility = self.create_facility(user=self.create_user())
        self.locations = []
        self.expected = {}

        grandparent = self.make_location()
        beds_only = self.make_location(parent=grandparent)
        sub_locations_only = self.make_location()
        mixed = self.make_location()
        deleted_children_only = self.make_location()
        empty = self.make_location()
        deleted_parent = self.make_location(deleted=True)

        # Mode determines the flags even when the physical form differs.
        self.make_location(parent=beds_only, mode="instance", form="ro")
        self.make_location(parent=sub_locations_only, mode="kind", form="bd")
        self.make_location(parent=mixed, mode="kind")
        self.make_location(parent=mixed, mode="instance")
        self.make_location(parent=deleted_children_only, mode="kind", deleted=True)
        self.make_location(parent=deleted_children_only, mode="instance", deleted=True)
        self.make_location(parent=deleted_parent, mode="instance")

        self.expected.update(
            {
                grandparent.pk: (True, True, False),
                beds_only.pk: (True, False, True),
                sub_locations_only.pk: (True, True, False),
                mixed.pk: (True, True, True),
                deleted_parent.pk: (True, False, True),
            }
        )
        locations = FacilityLocation._base_manager.all()  # noqa: SLF001
        locations.update(
            has_children=False,
            has_sub_locations=False,
            has_beds=False,
            cached_parent_json={"stale": True},
        )
        locations.filter(pk__in=[deleted_children_only.pk, empty.pk]).update(
            has_children=True,
            has_sub_locations=True,
            has_beds=True,
        )

    def make_location(self, **kwargs):
        location = baker.make(
            FacilityLocation,
            facility=self.facility,
            mode=kwargs.pop("mode", "kind"),
            form=kwargs.pop("form", "wa"),
            **kwargs,
        )
        self.locations.append(location)
        self.expected[location.pk] = (False, False, False)
        return location

    def assert_flags_repaired(self):
        for location in self.locations:
            with self.subTest(location=location.pk):
                location.refresh_from_db()
                self.assertEqual(
                    (
                        location.has_children,
                        location.has_sub_locations,
                        location.has_beds,
                    ),
                    self.expected[location.pk],
                )
                self.assertEqual(location.cached_parent_json, {})

    def test_migration_backfills_flags_and_clears_parent_caches(self):
        migration_module = import_module(f"care.emr.migrations.{self.migration}")
        historical_apps = (
            MigrationLoader(connection).project_state([("emr", self.migration)]).apps
        )
        migration_module.backfill_child_flags(
            historical_apps, connection.schema_editor()
        )
        self.assert_flags_repaired()
