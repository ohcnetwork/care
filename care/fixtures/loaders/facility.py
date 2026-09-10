from uuid import uuid4

from django.urls import reverse

from care.fixtures.base import generate_phone_number, log
from care.fixtures.loaders.load import load_json

_FACILITY_ROW_META = frozenset(
    {"ref", "geo_org_ref", "name_template", "description_template"}
)


def resolve_or_create_facility(
    base, *, facility_id=None, name=None, organization_ids_by_ref=None
) -> str:
    if facility_id:
        log(f"Using existing facility id={facility_id} (no new facilities created)")
        return facility_id

    return create_facilities_from_pack(
        base,
        organization_ids_by_ref,
        name=name,
    )


def create_facilities_from_pack(base, organization_ids_by_ref, *, name=None) -> str:
    rows = load_json("facilities")
    if not isinstance(rows, list) or not rows:
        msg = "facilities.json must be a non-empty list"
        raise ValueError(msg)

    seed_id = None
    seed_name = None
    for index, row in enumerate(rows):
        override_name = name if index == 0 else None
        created = _create_facility_from_row(
            base,
            organization_ids_by_ref,
            row,
            name=override_name,
        )
        ref = row.get("ref", f"row-{index}")
        if index == 0:
            seed_id = created.id
            seed_name = created.name
            log(f"Facility to seed: {created.name!r} (ref={ref}, id={created.id})")
        else:
            log(
                f"Extra facility (empty, for switcher only): {created.name!r} "
                f"(ref={ref}, id={created.id})"
            )

    log(
        f"Seeding pack data into {seed_name!r} only "
        f"({len(rows)} facilities created; extras stay empty)"
    )
    return seed_id


def geo_organization_id_for_facility(base, facility_id) -> str:
    """Return the facility's geo organization external id."""
    facility = base.get(reverse("facility-detail", kwargs={"external_id": facility_id}))
    geo = facility.geo_organization
    if not geo:
        msg = f"Facility {facility_id} has no geo_organization"
        raise ValueError(msg)
    return str(geo.id)


def _create_facility_from_row(base, organization_ids_by_ref, row, *, name=None):
    tokens = {"run_number": uuid4().hex[:8]}

    def render(template: str) -> str:
        return template.format(**tokens)

    geo_organization_id = organization_ids_by_ref[row["geo_org_ref"]]

    payload = {
        key: value for key, value in row.items() if key not in _FACILITY_ROW_META
    }
    return base.create_facility(
        geo_organization_id,
        name=name or render(row["name_template"]),
        description=render(row["description_template"]),
        facility_type=payload["facility_type"],
        address=payload["address"],
        pincode=payload["pincode"],
        phone_number=generate_phone_number(),
        latitude=payload["latitude"],
        longitude=payload["longitude"],
        is_public=payload["is_public"],
        features=payload["features"],
    )
