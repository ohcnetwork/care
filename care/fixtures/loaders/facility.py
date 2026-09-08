from uuid import uuid4

from django.urls import reverse

from care.emr.resources.organization.spec import OrganizationTypeChoices
from care.fixtures.base import generate_phone_number
from care.fixtures.loaders.load import load_json

_FACILITY_ROW_META = frozenset({"ref"})


def _log(message):
    print(message)  # noqa: T201


def find_organization_by_name(base, name, *, org_type=None, parent=None):
    params = {"name": name, "limit": 100}
    if org_type is not None:
        params["org_type"] = org_type
    if parent is not None:
        params["parent"] = parent
    data = base.get(reverse("organization-list"), params=params)
    for org in data.get("results", data):
        if org.name != name:
            continue
        if parent is None and org.parent:
            # A nested organization of the same name is not the root we want.
            continue
        return org
    return None


def get_or_create_organization(base, name, **kwargs):
    existing = find_organization_by_name(
        base,
        name,
        org_type=kwargs.get("org_type"),
        parent=kwargs.get("parent"),
    )
    if existing is not None:
        _log(f"Reusing organization {name!r}")
        return existing
    return base.create_organization(name=name, **kwargs)


def _create_facility_from_row(base, geo_organization_id, row, *, name=None):
    """Create one facility from a ``facilities.json`` row."""
    tokens = {"run_number": uuid4().hex[:8]}

    def render(template: str) -> str:
        return template.format(**tokens)

    payload = {
        key: value for key, value in row.items() if key not in _FACILITY_ROW_META
    }
    return base.create_facility(
        geo_organization_id,
        name=name or render(payload["name_template"]),
        description=render(payload["description_template"]),
        facility_type=payload["facility_type"],
        address=payload["address"],
        pincode=payload["pincode"],
        phone_number=generate_phone_number(),
        latitude=payload["latitude"],
        longitude=payload["longitude"],
        is_public=payload["is_public"],
        features=payload["features"],
    )


def create_facilities_from_pack(base, geo_organization_id, *, name=None) -> str:
    """Create every facility in pack ``facilities.json``; return the first id.

    The first row is the facility that later pack steps seed. Extra rows exist
    for the facility switcher (empty siblings) and are not seeded. ``name``
    overrides only the first row's ``name_template``.
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
            geo_organization_id,
            row,
            name=override_name,
        )
        if first_id is None:
            first_id = created.id
            _log(
                f"Created seed facility {created.id} name={created.name!r} "
                f"(ref={row.get('ref')!r})"
            )
        else:
            _log(
                f"Created empty facility {created.id} name={created.name!r} "
                f"(ref={row.get('ref')!r}; not seeded)"
            )

    _log(
        f"Pack will seed only the first facility {first_id} "
        f"({len(rows)} facilities created from facilities.json)"
    )
    return first_id


def resolve_or_create_facility(base, *, facility_id=None, name=None) -> str:
    """Return a facility external id: reuse ``facility_id`` or create from pack.

    When ``facility_id`` is set, it is returned as-is and no extra facilities
    are created (attach path). Otherwise get-or-create Kerala + Ernakulam,
    create every row in ``facilities.json``, and return the first facility id.
    """
    if facility_id:
        return facility_id

    geo_organization = get_or_create_organization(
        base,
        "Kerala",
        org_type=OrganizationTypeChoices.govt.value,
        metadata={
            "govt_org_type": "state",
            "govt_org_children_type": "district",
        },
    )
    district_organization = get_or_create_organization(
        base,
        "Ernakulam",
        org_type=OrganizationTypeChoices.govt.value,
        parent=geo_organization.id,
        metadata={
            "govt_org_type": "district",
            "govt_org_children_type": "local_body",
        },
    )
    return create_facilities_from_pack(
        base,
        district_organization.id,
        name=name,
    )
