from django.urls import reverse

from care.fixtures.loaders.load import load_json

_ORG_ROW_META = frozenset({"ref", "parent_ref", "managing_organization_refs"})


def load_organizations(base) -> dict[str, str]:
    pack = load_json("organizations")
    organization_ids_by_ref: dict[str, str] = {}
    managing_links: list[tuple[str, list[str]]] = []

    for entry in pack.get("organizations", []):
        ref = entry["ref"]
        parent_ref = entry.get("parent_ref")
        managing_refs = entry.get("managing_organization_refs") or []
        payload = {
            key: value for key, value in entry.items() if key not in _ORG_ROW_META
        }
        if parent_ref:
            payload["parent"] = organization_ids_by_ref[parent_ref]

        name = payload.pop("name")
        created = get_or_create_organization(base, name, **payload)
        organization_ids_by_ref[ref] = str(created.id)
        if managing_refs:
            managing_links.append((ref, managing_refs))

    # Second pass so manager orgs can appear later in the pack than managed ones.
    for role_ref, managing_refs in managing_links:
        role_org_id = organization_ids_by_ref[role_ref]
        for managing_ref in managing_refs:
            base.link_managing_org(role_org_id, organization_ids_by_ref[managing_ref])

    return organization_ids_by_ref


def get_or_create_organization(base, name, **kwargs):
    existing = find_organization_by_name(
        base,
        name,
        org_type=kwargs.get("org_type"),
        parent=kwargs.get("parent"),
    )
    if existing is not None:
        return existing
    return base.create_organization(name=name, **kwargs)


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
