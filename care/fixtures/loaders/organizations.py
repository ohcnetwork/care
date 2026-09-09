from django.urls import reverse

from care.fixtures.base import log
from care.fixtures.loaders.load import load_json

_ORG_ROW_META = frozenset({"ref", "parent_ref"})


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
        log(f"Reusing organization {name!r}")
        return existing
    return base.create_organization(name=name, **kwargs)


def load_organizations(base) -> dict[str, str]:
    pack = load_json("organizations")
    organization_ids_by_ref: dict[str, str] = {}

    for entry in pack.get("organizations", []):
        ref = entry["ref"]
        parent_ref = entry.get("parent_ref")
        payload = {
            key: value for key, value in entry.items() if key not in _ORG_ROW_META
        }
        if parent_ref:
            payload["parent"] = organization_ids_by_ref[parent_ref]

        name = payload.pop("name")
        created = get_or_create_organization(base, name, **payload)
        organization_ids_by_ref[ref] = str(created.id)
        log(f"Organization {name!r} ({ref})")

    return organization_ids_by_ref
