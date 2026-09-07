import secrets
from uuid import uuid4

from django.urls import reverse

from care.emr.resources.organization.spec import OrganizationTypeChoices
from care.fixtures.loaders.load import load_json


def _log(message):
    print(message)  # noqa: T201


def find_organization_by_name(base, name, *, parent=None):
    params = {"name": name, "limit": 100}
    if parent is not None:
        params["parent"] = parent
    data = base.get(reverse("organization-list"), params=params)
    for org in data.get("results", data):
        if org.name == name:
            return org
    return None


def get_or_create_organization(base, name, **kwargs):
    parent = kwargs.get("parent")
    existing = find_organization_by_name(base, name, parent=parent)
    if existing is not None:
        _log(f"Reusing organization {name!r}")
        return existing
    return base.create_organization(name=name, **kwargs)


def create_facility_from_pack(base, geo_organization_id, *, name=None):
    """Create a facility from pack ``facility.json``.

    Resolves ``run_number`` / ``local_number`` templates. When ``name`` is
    provided it overrides ``name_template``; otherwise the rendered template
    is used.
    """
    pack = load_json("facility")
    tokens = {
        "run_number": uuid4().hex[:8],
        "local_number": f"{secrets.randbelow(10**10):010d}",
    }

    def render(template: str) -> str:
        return template.format(**tokens)

    return base.create_facility(
        geo_organization_id,
        name=name or render(pack["name_template"]),
        description=render(pack["description_template"]),
        facility_type=pack["facility_type"],
        address=pack["address"],
        pincode=pack["pincode"],
        phone_number=render(pack["phone_number_template"]),
        latitude=pack["latitude"],
        longitude=pack["longitude"],
        is_public=pack["is_public"],
        features=pack["features"],
    )


def resolve_or_create_facility(base, *, facility_id=None, name=None) -> str:
    """Return a facility external id: reuse ``facility_id`` or create from pack.

    When ``facility_id`` is set, it is returned as-is (caller may log attach).
    Otherwise get-or-create Kerala + Ernakulam, create a facility under
    Ernakulam from pack ``facility.json``, and return the new facility id.
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
    facility = create_facility_from_pack(
        base,
        district_organization.id,
        name=name,
    )
    _log(
        f"Created facility {facility.id} name={facility.name!r} "
        "(from facility.json; no PACK_FACILITY_ID set)"
    )
    return facility.id
