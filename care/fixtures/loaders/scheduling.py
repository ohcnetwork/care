from datetime import timedelta

from care.fixtures.loaders.load import load_json
from care.utils.time_util import care_now

_TOKEN_CATEGORY_ROW_META = frozenset({"ref", "default"})
_SCHEDULE_ROW_META = frozenset({"ref", "user_ref", "valid_days"})
_TOKEN_QUEUE_ROW_META = frozenset({"ref", "user_ref", "sub_queues"})
_SLOT_SEARCH_DAYS = 7


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


def load_token_queues(base, facility_id, user_ids_by_ref) -> dict[str, str]:
    pack = load_json("token_queues")
    token_queue_ids_by_ref: dict[str, str] = {}

    for entry in pack.get("queues", []):
        ref = entry["ref"]
        user_ref = entry["user_ref"]
        resource_type = entry["resource_type"]
        resource_id = user_ids_by_ref[user_ref]
        booking_date, _slots = _first_day_with_slots(
            base, facility_id, resource_type, resource_id
        )
        payload = {
            key: value
            for key, value in entry.items()
            if key not in _TOKEN_QUEUE_ROW_META and key != "resource_type"
        }
        queue = base.create_token_queue(
            facility_id,
            resource_type,
            resource_id,
            date=booking_date,
            **payload,
        )
        token_queue_ids_by_ref[ref] = queue.id

        for sub_queue in entry.get("sub_queues", []):
            base.create_token_sub_queue(
                facility_id,
                resource_type,
                resource_id,
                **sub_queue,
            )

    return token_queue_ids_by_ref


def load_appointments(base, facility_id, user_ids_by_ref, patient_ids_by_ref) -> None:
    pack = load_json("appointments")
    slots_by_user_ref: dict[str, list] = {}

    for entry in pack.get("appointments", []):
        user_ref = entry["user_ref"]
        resource_type = entry["resource_type"]
        if user_ref not in slots_by_user_ref:
            resource_id = user_ids_by_ref[user_ref]
            _booking_date, slots = _first_day_with_slots(
                base, facility_id, resource_type, resource_id
            )
            slots_by_user_ref[user_ref] = slots

        slot = slots_by_user_ref[user_ref][entry["slot_index"]]
        note = entry.get("note", "")
        base.create_appointment(
            facility_id,
            slot_id=slot.id,
            patient_id=patient_ids_by_ref[entry["patient_ref"]],
            note=note,
        )


def _first_day_with_slots(base, facility_id, resource_type, resource_id):
    """Return (date_iso, slots) for the first day from tomorrow with slots."""
    day = care_now().date() + timedelta(days=1)
    for _ in range(_SLOT_SEARCH_DAYS):
        response = base.get_slots_for_day(
            facility_id,
            resource_type,
            resource_id,
            day.isoformat(),
        )
        slots = response.get("results", [])
        if slots:
            return day.isoformat(), slots
        day += timedelta(days=1)
    msg = (
        f"No slots for {resource_type}/{resource_id} "
        f"within {_SLOT_SEARCH_DAYS} days from tomorrow"
    )
    raise LookupError(msg)
