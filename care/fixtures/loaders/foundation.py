from care.fixtures.loaders.load import load_json

_DEPT_META = frozenset({"ref", "reuse_existing"})
_LOCATION_META = frozenset({"ref", "parent_ref", "organization_refs"})
_SERVICE_META = frozenset({"ref", "managing_organization_ref", "location_refs"})


def _resource_id(resource) -> str:
    if isinstance(resource, dict):
        return str(resource["id"])
    return str(resource.id)


def _find_org_by_name(organizations, name: str):
    for org in organizations:
        org_name = org["name"] if isinstance(org, dict) else org.name
        if org_name == name:
            return org
    return None


def load_facility_foundation(base, facility_id):
    """Load departments, locations, and healthcare services from pack JSON.

    Returns ``(stats, resource_ids_by_ref)`` where ``resource_ids_by_ref`` maps
    pack ``ref`` strings to resource external ids for later pack steps.
    """
    pack = load_json("facility_foundation")
    resource_ids_by_ref: dict[str, str] = {}
    stats = {
        "departments": 0,
        "departments_reused": 0,
        "locations": 0,
        "healthcare_services": 0,
    }

    existing_orgs = base.get_facility_organizations(facility_id)
    for department in pack.get("departments", []):
        ref = department["ref"]
        if department.get("reuse_existing"):
            org = _find_org_by_name(existing_orgs, department["name"])
            if org is None:
                msg = (
                    "Could not reuse facility organization named "
                    f"{department['name']!r} for {ref}"
                )
                raise ValueError(msg)
            resource_ids_by_ref[ref] = _resource_id(org)
            stats["departments_reused"] += 1
            continue

        payload = {k: v for k, v in department.items() if k not in _DEPT_META}
        created = base.create_facility_organization(facility_id, **payload)
        resource_ids_by_ref[ref] = _resource_id(created)
        stats["departments"] += 1

    for location in pack.get("locations", []):
        ref = location["ref"]
        payload = {k: v for k, v in location.items() if k not in _LOCATION_META}
        parent_ref = location.get("parent_ref")
        if parent_ref:
            if parent_ref not in resource_ids_by_ref:
                msg = f"Missing parent ref {parent_ref!r} for location {ref}"
                raise ValueError(msg)
            payload["parent"] = resource_ids_by_ref[parent_ref]

        org_refs = location.get("organization_refs") or []
        if org_refs:
            missing = [
                org_ref for org_ref in org_refs if org_ref not in resource_ids_by_ref
            ]
            if missing:
                msg = f"Missing organization refs {missing!r} for location {ref}"
                raise ValueError(msg)
            payload["organizations"] = [
                resource_ids_by_ref[org_ref] for org_ref in org_refs
            ]
        else:
            # Field is required on write; empty list is valid (same as UI/seedpack).
            payload["organizations"] = []

        created = base.create_location(facility_id, **payload)
        resource_ids_by_ref[ref] = _resource_id(created)
        stats["locations"] += 1

    for service in pack.get("healthcare_services", []):
        ref = service["ref"]
        payload = {k: v for k, v in service.items() if k not in _SERVICE_META}
        name = payload.pop("name")

        org_ref = service.get("managing_organization_ref")
        if org_ref:
            payload["managing_organization"] = resource_ids_by_ref[org_ref]

        location_refs = service.get("location_refs") or []
        if location_refs:
            payload["locations"] = [
                resource_ids_by_ref[loc_ref] for loc_ref in location_refs
            ]

        created = base.create_healthcare_service(facility_id, name, **payload)
        resource_ids_by_ref[ref] = _resource_id(created)
        stats["healthcare_services"] += 1

    return stats, resource_ids_by_ref
