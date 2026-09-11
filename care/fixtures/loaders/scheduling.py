from datetime import timedelta

from care.fixtures.loaders.load import load_json
from care.utils.time_util import care_now

_TOKEN_CATEGORY_ROW_META = frozenset({"ref", "default"})
_SCHEDULE_ROW_META = frozenset({"ref", "user_ref", "valid_days"})


def load_token_categories(base, facility_id) -> dict[str, str]:
    pack = load_json("token_categories")
    token_category_ids_by_ref: dict[str, str] = {}

    for entry in pack.get("categories", []):
        ref = entry["ref"]
        resource_type = entry["resource_type"]
        payload = {
            key: value
            for key, value in entry.items()
            if key not in _TOKEN_CATEGORY_ROW_META and key != "resource_type"
        }
        category = base.create_token_category(facility_id, resource_type, **payload)
        if entry.get("default"):
            base.set_token_category_default(facility_id, category.id)
        token_category_ids_by_ref[ref] = category.id

    return token_category_ids_by_ref


def load_schedules(base, facility_id, user_ids_by_ref) -> dict[str, str]:
    pack = load_json("schedules")
    schedule_ids_by_ref: dict[str, str] = {}
    now = care_now()

    for entry in pack.get("schedules", []):
        ref = entry["ref"]
        user_ref = entry["user_ref"]
        valid_days = entry["valid_days"]
        resource_type = entry["resource_type"]
        resource_id = user_ids_by_ref[user_ref]

        payload = {
            key: value
            for key, value in entry.items()
            if key not in _SCHEDULE_ROW_META and key != "resource_type"
        }
        payload["valid_from"] = (now + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00")
        payload["valid_to"] = (now + timedelta(days=valid_days)).strftime(
            "%Y-%m-%dT23:59:59"
        )

        schedule = base.create_schedule(
            facility_id,
            resource_type,
            resource_id,
            **payload,
        )
        schedule_ids_by_ref[ref] = schedule.id

    return schedule_ids_by_ref
