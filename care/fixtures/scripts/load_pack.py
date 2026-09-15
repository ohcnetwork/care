"""Load a pack into a facility: orgs, questionnaires, foundation, users,
schedules, patients, queues, appointments, encounters, clinical content,
definitions, billing, stock.

Order: organizations → facility (create or attach) → questionnaires →
templates → foundation (incl. devices) → users → token categories →
schedules → patients → token queues → appointments → encounters →
specimen → observation → resource categories → product knowledge →
charge item definitions → activity definitions → clinical content →
billing → external receipts → internal transfers.

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

``include_users=False`` skips pack ``users.json`` (e.g. Experience seeds its
own accounts). Pass ``user_ids_by_ref`` mapping every pack user ref used by
schedules, queues, appointments, and clinical service requests — otherwise
``load_pack`` fails before those stages instead of KeyError mid-run.
"""

import os

from care.fixtures.base import FixtureError, log
from care.fixtures.context import care_fixture_context
from care.fixtures.loaders.billing import load_billing
from care.fixtures.loaders.clinical_visits import (
    load_clinical_content,
    load_clinical_encounters,
)
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
from care.fixtures.loaders.load import load_json
from care.fixtures.loaders.organizations import load_organizations
from care.fixtures.loaders.patients import load_patients
from care.fixtures.loaders.questionnaires import load_questionnaires
from care.fixtures.loaders.scheduling import (
    load_appointments,
    load_schedules,
    load_token_categories,
    load_token_queues,
)
from care.fixtures.loaders.templates import load_templates
from care.fixtures.loaders.users import load_users


def load_pack(  # noqa: PLR0915
    base,
    facility_id=None,
    facility_name=None,
    *,
    include_users=True,
    user_ids_by_ref=None,
):
    attaching = bool(facility_id)
    if attaching and facility_name:
        log("Ignoring facility_name: it applies only when creating a facility")

    organization_ids_by_ref = load_organizations(base)
    log("Loaded organizations")

    facility_id, facility_names = resolve_or_create_facility(
        base,
        facility_id=facility_id,
        name=facility_name,
        organization_ids_by_ref=organization_ids_by_ref,
    )
    log(f"Loaded facilities ({', '.join(facility_names)})")

    load_questionnaires(base, organization_ids_by_ref)
    log("Loaded questionnaires")

    load_templates(base, facility_id)
    log("Loaded templates")

    foundation_resource_id_by_ref = load_facility_foundation(base, facility_id)
    log("Loaded facility foundation")

    if include_users:
        user_ids_by_ref = load_users(
            base,
            facility_id,
            foundation_resource_id_by_ref,
            organization_ids_by_ref,
        )
        log("Loaded users")
    else:
        user_ids_by_ref = _require_user_ids_by_ref(user_ids_by_ref or {})
        log("Skipped pack users (include_users=False); using caller user_ids_by_ref")

    load_token_categories(base, facility_id)
    log("Loaded token categories")

    load_schedules(base, facility_id, user_ids_by_ref)
    log("Loaded schedules")

    patient_ids_by_ref = load_patients(base, facility_id, organization_ids_by_ref)
    log("Loaded patients")

    load_token_queues(base, facility_id, user_ids_by_ref)
    log("Loaded token queues")

    load_appointments(base, facility_id, user_ids_by_ref, patient_ids_by_ref)
    log("Loaded appointments")

    (
        encounter_ids_by_ref,
        patient_id_by_encounter_ref,
        close_after,
        period_start_by_encounter_ref,
    ) = load_clinical_encounters(
        base,
        facility_id,
        patient_ids_by_ref,
        foundation_resource_id_by_ref,
    )
    log("Loaded clinical encounters")

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

    load_clinical_content(
        base,
        facility_id,
        encounter_ids_by_ref,
        patient_id_by_encounter_ref,
        product_knowledge_by_ref,
        period_start_by_encounter_ref,
        user_ids_by_ref,
        close_after=close_after,
    )
    log("Loaded clinical data for encounters")

    load_billing(
        base,
        facility_id,
        patient_ids_by_ref,
        encounter_ids_by_ref,
        charge_item_definitions_by_ref,
    )
    log("Loaded billing")

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


def pack_required_user_refs() -> set[str]:
    """User refs required by schedules, queues, appointments, and clinical SRs."""
    refs: set[str] = set()
    for entry in load_json("schedules").get("schedules", []):
        refs.add(entry["user_ref"])
    for entry in load_json("token_queues").get("queues", []):
        refs.add(entry["user_ref"])
    for entry in load_json("appointments").get("appointments", []):
        refs.add(entry["user_ref"])
    for entry in load_json("clinical_content").get("service_requests", []):
        requester = entry.get("requester_user_ref")
        if requester:
            refs.add(requester)
    return refs


def _require_user_ids_by_ref(user_ids_by_ref: dict) -> dict:
    required = pack_required_user_refs()
    missing = sorted(required - set(user_ids_by_ref))
    if missing:
        msg = (
            "include_users=False requires user_ids_by_ref for pack stages that "
            f"reference users; missing: {missing}"
        )
        raise FixtureError(msg)
    return user_ids_by_ref
