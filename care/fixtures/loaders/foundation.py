from care.fixtures.loaders.load import load_json

_DEPT_META = frozenset({"ref", "reuse_existing"})
_LOCATION_META = frozenset({"ref", "parent_ref", "organization_refs"})
_SERVICE_META = frozenset({"ref", "managing_organization_ref", "location_refs"})


def load_facility_foundation(base, facility_id):
    """Load departments, locations, and healthcare services from pack JSON.

    Returns a mapping from pack ``ref`` strings to resource external ids for
    later pack steps.
    """
    pack = load_json("facility_foundation")
    foundation_resource_id_by_ref: dict[str, str] = {}

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
            foundation_resource_id_by_ref[ref] = str(org.id)
            continue

        payload = {k: v for k, v in department.items() if k not in _DEPT_META}
        created = base.create_facility_organization(facility_id, **payload)
        foundation_resource_id_by_ref[ref] = str(created.id)

    for location in pack.get("locations", []):
        ref = location["ref"]
        payload = {k: v for k, v in location.items() if k not in _LOCATION_META}
        parent_ref = location.get("parent_ref")
        if parent_ref:
            payload["parent"] = foundation_resource_id_by_ref[parent_ref]

        org_refs = location.get("organization_refs") or []
        payload["organizations"] = [
            foundation_resource_id_by_ref[org_ref] for org_ref in org_refs
        ]

        created = base.create_location(facility_id, **payload)
        foundation_resource_id_by_ref[ref] = str(created.id)
        for organization_id in payload["organizations"]:
            base.add_organization_to_location(facility_id, created.id, organization_id)

    for service in pack.get("healthcare_services", []):
        ref = service["ref"]
        payload = {k: v for k, v in service.items() if k not in _SERVICE_META}
        name = payload.pop("name")

        org_ref = service.get("managing_organization_ref")
        if org_ref:
            payload["managing_organization"] = foundation_resource_id_by_ref[org_ref]

        location_refs = service.get("location_refs") or []
        if location_refs:
            payload["locations"] = [
                foundation_resource_id_by_ref[loc_ref] for loc_ref in location_refs
            ]

        created = base.create_healthcare_service(facility_id, name, **payload)
        foundation_resource_id_by_ref[ref] = str(created.id)

    return foundation_resource_id_by_ref


def _find_org_by_name(organizations, name: str):
    for org in organizations:
        if org.name == name:
            return org
    return None
