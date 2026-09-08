"""Load pack facility foundation, catalogues, activities, and initial stock.

Uses CareFixtureBase atomic helpers, not ``create_lab_test``.

Order: foundation (depts → locations → HS) → specimen → observation →
resource categories → product knowledge → charge item definitions → activity
definitions.

Run::

    PACK_FACILITY_ID=<uuid> python manage.py load_fixtures \\
        --path care/fixtures/scripts/load_pack.py

If ``PACK_FACILITY_ID`` is unset, reuses Kerala (or creates it) and creates
a facility from pack ``facility.json``. Optional ``PACK_FACILITY_NAME`` /
``facility_name=`` overrides the resolved name template.
"""

import os

from care.fixtures.context import care_fixture_context
from care.fixtures.loaders.catalogues import (
    load_activity_definitions,
    load_charge_item_definitions,
    load_observation_definitions,
    load_product_knowledge,
    load_resource_categories,
    load_specimen_definitions,
)
from care.fixtures.loaders.facility import resolve_or_create_facility
from care.fixtures.loaders.foundation import load_facility_foundation


def log(message):
    print(message)  # noqa: T201


def load_pack(base, facility_id=None, facility_name=None):
    facility_id = facility_id or os.environ.get("PACK_FACILITY_ID")
    if facility_id:
        log(f"Using PACK_FACILITY_ID={facility_id}")

    facility_id = resolve_or_create_facility(
        base,
        facility_id=facility_id,
        name=facility_name or os.environ.get("PACK_FACILITY_NAME"),
    )
    log(f"Loading pack foundation + catalogues + activities into {facility_id}")

    foundation_resource_id_by_ref = load_facility_foundation(base, facility_id)
    log("Loaded facility foundation")

    load_specimen_definitions(base, facility_id)
    log("Loaded specimen definitions")

    load_observation_definitions(base, facility_id)
    log("Loaded observation definitions")

    load_resource_categories(base, facility_id)
    log("Loaded resource categories")

    load_product_knowledge(base, facility_id)
    log("Loaded product knowledge")

    load_charge_item_definitions(base, facility_id)
    log("Loaded charge item definitions")

    load_activity_definitions(base, facility_id, foundation_resource_id_by_ref)
    log("Loaded activity definitions")

    log("Pack load complete")


if __name__ == "__main__":
    with care_fixture_context() as base:
        load_pack(base)
