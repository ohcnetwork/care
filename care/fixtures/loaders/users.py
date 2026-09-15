from django.urls import reverse

from care.fixtures.base import generate_phone_number, log
from care.fixtures.loaders.facility import geo_organization_id_for_facility
from care.fixtures.loaders.load import load_json

_USER_ROW_META = frozenset({"ref", "role_name", "role_org_ref", "facility_org_ref"})


def load_users(
    base, facility_id, foundation_resource_id_by_ref, organization_ids_by_ref=None
):
    organization_ids_by_ref = organization_ids_by_ref or {}
    pack = load_json("users")
    password = pack.get("password", "Ohcn@123")
    roles = base.get_roles()
    geo_organization_id = geo_organization_id_for_facility(base, facility_id)
    existing_by_username = _existing_users_by_username(base)
    role_org_members: dict[str, set[str]] = {}
    facility_org_members: dict[str, set[str]] = {}
    user_ids_by_ref: dict[str, str] = {}
    credentials: list[tuple[str, str, bool]] = []

    for entry in pack.get("users", []):
        ref = entry["ref"]
        username = entry["username"]
        role_name = entry["role_name"]
        role_org_ref = entry.get("role_org_ref")
        facility_org_ref = entry.get("facility_org_ref")

        role = roles[role_name]

        role_org_id = organization_ids_by_ref[role_org_ref] if role_org_ref else None
        role_orgs_payload = []
        if role_org_id:
            role_orgs_payload = [{"organization": role_org_id, "role": role.id}]

        existing = existing_by_username.get(username)
        if existing is not None:
            user = existing
            created = False
            if role_org_id:
                _ensure_role_org_membership(
                    base, role_org_id, user.id, role.id, role_org_members
                )
        else:
            payload = {k: v for k, v in entry.items() if k not in _USER_ROW_META}
            user = base.create_user(
                geo_organization_id,
                role_orgs=role_orgs_payload,
                password=password,
                phone_number=generate_phone_number(),
                **payload,
            )
            created = True
            existing_by_username[username] = user
            if role_org_id:
                _role_org_member_ids(base, role_org_id, role_org_members).add(user.id)

        user_id = user.id
        if facility_org_ref:
            _ensure_facility_membership(
                base,
                facility_id,
                foundation_resource_id_by_ref[facility_org_ref],
                user_id,
                role.id,
                facility_org_members,
            )

        user_ids_by_ref[ref] = user_id
        credentials.append((username, role_name, created))

    log("Pack user credentials:")
    for username, role_name, created in credentials:
        pwd = password if created else "(existing)"
        log(f"  {username:<22} {pwd:<12} {role_name}")

    return user_ids_by_ref


def _existing_users_by_username(base) -> dict:
    """List users once; avoid detail GETs that 404 on first create."""
    results = base.list_all(reverse("users-list"))
    return {u.username: u for u in results}


def _user_ids_from_org_user_rows(results) -> set[str]:
    return {row.user.id for row in results if row.user is not None}


def _role_org_member_ids(base, org_id, cache: dict[str, set[str]]) -> set[str]:
    if org_id not in cache:
        results = base.list_all(
            reverse(
                "organization-users-list",
                kwargs={"organization_external_id": org_id},
            ),
        )
        cache[org_id] = _user_ids_from_org_user_rows(results)
    return cache[org_id]


def _facility_org_member_ids(
    base, facility_id, org_id, cache: dict[str, set[str]]
) -> set[str]:
    if org_id not in cache:
        results = base.list_all(
            reverse(
                "facility-organization-users-list",
                kwargs={
                    "facility_external_id": facility_id,
                    "facility_organizations_external_id": org_id,
                },
            ),
        )
        cache[org_id] = _user_ids_from_org_user_rows(results)
    return cache[org_id]


def _ensure_role_org_membership(base, role_org_id, user_id, role_id, cache):
    members = _role_org_member_ids(base, role_org_id, cache)
    if user_id in members:
        return
    base.assign_org_role(role_org_id, user_id, role_id)
    members.add(user_id)


def _ensure_facility_membership(base, facility_id, org_id, user_id, role_id, cache):
    members = _facility_org_member_ids(base, facility_id, org_id, cache)
    if user_id in members:
        return
    base.add_user_to_facility_organization(facility_id, org_id, user_id, role_id)
    members.add(user_id)
