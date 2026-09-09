"""Load a pack into a facility: orgs, foundation, users, patients, definitions, stock.

Order: organizations → facility (create or attach) → foundation → users →
patients → specimen → observation → resource categories → product knowledge →
charge item definitions → activity definitions → external receipts →
internal transfers.

As a script -- ``PACK_FACILITY_ID`` and ``PACK_FACILITY_NAME`` are read only by
the ``__main__`` block below::

    PACK_FACILITY_ID=<uuid> python manage.py load_fixtures \\
        --path care/fixtures/scripts/load_pack.py

As a function -- plugins, tests, other scripts::

    with care_fixture_context() as base:
        load_pack(base, facility_id=existing_facility_id)

Without a facility id, pack organizations are get-or-created and every row in
pack ``facilities.json`` is created; definitions and stock load into the
**first** facility only. Extra facilities stay empty (facility switcher).
When ``facility_id`` is given (attach / plugin / ``PACK_FACILITY_ID``), no
extra facilities are created — only that facility is seeded. Organizations
still load (suppliers for receipts; geo get-or-create is idempotent).
"""

import os

from care.fixtures.base import log
from care.fixtures.context import care_fixture_context
from care.fixtures.loaders.definitions import (
    load_activity_definitions,
    load_charge_item_definitions,
    load_observation_definitions,
    load_product_knowledge,
    load_resource_categories,
    load_specimen_definitions,
)
from care.fixtures.loaders.external_receipts import load_external_receipts
from care.fixtures.loaders.facility import resolve_or_create_facility
from care.fixtures.loaders.foundation import load_facility_foundation
from care.fixtures.loaders.internal_transfers import load_internal_transfers
from care.fixtures.loaders.organizations import load_organizations
from care.fixtures.loaders.patients import load_patients
from care.fixtures.loaders.users import load_users


def load_pack(base, facility_id=None, facility_name=None):
    if facility_id:
        log(f"Attaching to existing facility {facility_id}")
        if facility_name:
            log("Ignoring facility_name: it applies only when creating a facility")

    organization_ids_by_ref = load_organizations(base)
    log("Loaded organizations")

    facility_id = resolve_or_create_facility(
        base,
        facility_id=facility_id,
        name=facility_name,
        organization_ids_by_ref=organization_ids_by_ref,
    )
    log(
        f"Loading pack foundation + users + patients + definitions + activities "
        f"into {facility_id}"
    )

    foundation_resource_id_by_ref = load_facility_foundation(base, facility_id)
    log("Loaded facility foundation")

    load_users(base, facility_id, foundation_resource_id_by_ref)
    log("Loaded users")

    load_patients(base, facility_id, organization_ids_by_ref)
    log("Loaded patients")

    load_specimen_definitions(base, facility_id)
    log("Loaded specimen definitions")

    load_observation_definitions(base, facility_id)
    log("Loaded observation definitions")

    load_resource_categories(base, facility_id)
    log("Loaded resource categories")

    product_knowledge_by_ref = load_product_knowledge(base, facility_id)
    log("Loaded product knowledge")

    charge_item_definitions_by_ref = load_charge_item_definitions(base, facility_id)
    log("Loaded charge item definitions")

    load_activity_definitions(base, facility_id, foundation_resource_id_by_ref)
    log("Loaded activity definitions")

    product_ids_by_ref = load_external_receipts(
        base,
        facility_id,
        foundation_resource_id_by_ref,
        product_knowledge_by_ref,
        charge_item_definitions_by_ref,
        organization_ids_by_ref,
    )
    log("Loaded external receipts")

    load_internal_transfers(
        base,
        facility_id,
        foundation_resource_id_by_ref,
        product_knowledge_by_ref,
        product_ids_by_ref,
    )
    log("Loaded internal transfers")
    log("Pack load complete")


if __name__ == "__main__":
    with care_fixture_context() as base:
        load_pack(
            base,
            facility_id=os.environ.get("PACK_FACILITY_ID"),
            facility_name=os.environ.get("PACK_FACILITY_NAME"),
        )
