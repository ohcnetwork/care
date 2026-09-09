from care.fixtures.base import FixtureError, generate_phone_number, log
from care.fixtures.loaders.facility import geo_organization_id_for_facility
from care.fixtures.loaders.load import load_json

_EMAIL_DOMAIN = "example.com"


def _get_or_create_user(base, geo_organization_id, password, entry):
    username = entry["username"]
    try:
        return base.get_user(username), False
    except FixtureError:
        pass

    return (
        base.create_user(
            geo_organization_id,
            role_orgs=[],
            username=username,
            email=f"{username}@{_EMAIL_DOMAIN}",
            password=password,
            first_name=entry.get("first_name", "Care"),
            last_name=entry.get("last_name", "User"),
            gender=entry.get("gender", "female"),
            phone_number=generate_phone_number(),
        ),
        True,
    )


def _ensure_facility_membership(base, facility_id, org_id, user_id, role_id):
    try:
        base.add_user_to_facility_organization(facility_id, org_id, user_id, role_id)
    except FixtureError as exc:
        if "already exists" not in str(exc).lower():
            raise


def load_users(base, facility_id, foundation_resource_id_by_ref):
    pack = load_json("users")
    password = pack.get("password", "Ohcn@123")
    roles = base.get_roles()
    geo_organization_id = geo_organization_id_for_facility(base, facility_id)
    user_ids_by_ref: dict[str, str] = {}
    credentials: list[tuple[str, str, str]] = []

    for entry in pack.get("users", []):
        ref = entry["ref"]
        username = entry["username"]
        role_name = entry["role_name"]
        facility_org_ref = entry.get("facility_org_ref")

        role = roles.get(role_name)
        if role is None:
            msg = f"Role {role_name!r} not found for {ref}"
            raise ValueError(msg)

        user, created = _get_or_create_user(base, geo_organization_id, password, entry)
        user_id = str(user.id)

        if facility_org_ref:
            org_id = foundation_resource_id_by_ref[facility_org_ref]
            _ensure_facility_membership(
                base, facility_id, org_id, user_id, str(role.id)
            )
            membership = f"→ {facility_org_ref} as {role_name}"
        else:
            membership = f"as {role_name} (no facility org)"

        user_ids_by_ref[ref] = user_id
        credentials.append((username, role_name, "created" if created else "reused"))
        log(f"{'Created' if created else 'Reused'} user {username!r} {membership}")

    log("Pack user credentials (password from users.json):")
    for username, role_name, status in credentials:
        log(f"  {username:<22} {password:<12} {role_name:<16} ({status})")

    return user_ids_by_ref
