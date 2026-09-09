from uuid import uuid4

from django.urls import reverse

from care.fixtures.base import generate_phone_number, log
from care.fixtures.loaders.load import load_json

_FACILITY_ROW_META = frozenset(
    {"ref", "geo_org_ref", "name_template", "description_template"}
)


def geo_organization_id_for_facility(base, facility_id) -> str:
    """Return the facility's geo organization external id."""
    facility = base.get(reverse("facility-detail", kwargs={"external_id": facility_id}))
    geo = facility.geo_organization
    if not geo:
        msg = f"Facility {facility_id} has no geo_organization"
        raise ValueError(msg)
    return str(geo.id)


def _create_facility_from_row(base, organization_ids_by_ref, row, *, name=None):
    """Create one facility from a ``facilities.json`` row."""
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


def create_facilities_from_pack(base, organization_ids_by_ref, *, name=None) -> str:
    """Create every facility in pack ``facilities.json``; return the first id.

    The first row is the facility that later pack steps seed. Extra rows exist
    for the facility switcher (empty siblings) and are not seeded. ``name``
    overrides only the first row's ``name_template``. Each row requires
    ``geo_org_ref`` resolved from ``organization_ids_by_ref``.
    """
    rows = load_json("facilities")
    if not isinstance(rows, list) or not rows:
        msg = "facilities.json must be a non-empty list"
        raise ValueError(msg)

    first_id = None
    for index, row in enumerate(rows):
        override_name = name if index == 0 else None
        created = _create_facility_from_row(
            base,
            organization_ids_by_ref,
            row,
            name=override_name,
        )
        if first_id is None:
            first_id = created.id
            log(
                f"Created seed facility {created.id} name={created.name!r} "
                f"(ref={row.get('ref')!r})"
            )
        else:
            log(
                f"Created empty facility {created.id} name={created.name!r} "
                f"(ref={row.get('ref')!r}; not seeded)"
            )

    log(
        f"Pack will seed only the first facility {first_id} "
        f"({len(rows)} facilities created from facilities.json)"
    )
    return first_id


def resolve_or_create_facility(
    base, *, facility_id=None, name=None, organization_ids_by_ref=None
) -> str:
    """Return a facility external id: reuse ``facility_id`` or create from pack.

    When ``facility_id`` is set, it is returned as-is and no extra facilities
    are created (attach path). Otherwise create every row in
    ``facilities.json`` using ``organization_ids_by_ref`` for ``geo_org_ref``.
    """
    if facility_id:
        return facility_id

    return create_facilities_from_pack(
        base,
        organization_ids_by_ref,
        name=name,
    )
