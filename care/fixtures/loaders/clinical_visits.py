from datetime import UTC, datetime, timedelta

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from care.fixtures.loaders.load import facility_slug, load_json

_ENCOUNTER_ROW_META = frozenset(
    {"ref", "patient_ref", "organization_refs", "bed_ref", "days_ago"}
)
_CONDITION_ROW_META = frozenset(
    {"ref", "encounter_ref", "onset_days_before", "onset_hours_before"}
)
_COMPLETED_ENCOUNTER_DURATION = timedelta(minutes=45)


def load_clinical_encounters(
    base,
    facility_id,
    patient_ids_by_ref,
    foundation_resource_id_by_ref,
) -> tuple[dict[str, str], dict[str, str], list[dict], dict[str, str]]:
    pack = load_json("encounters")
    encounter_ids_by_ref: dict[str, str] = {}
    patient_id_by_encounter_ref: dict[str, str] = {}
    period_start_by_encounter_ref: dict[str, str] = {}
    close_after: list[dict] = []

    for entry in pack.get("encounters", []):
        ref = entry["ref"]
        patient_id = patient_ids_by_ref[entry["patient_ref"]]
        org_ids = [
            foundation_resource_id_by_ref[org_ref]
            for org_ref in entry["organization_refs"]
        ]
        payload = {
            key: value for key, value in entry.items() if key not in _ENCOUNTER_ROW_META
        }
        payload.setdefault("priority", "routine")
        desired_status = payload["status"]
        period = _period_from_days_ago(entry["days_ago"], desired_status)
        payload["period"] = {"start": period["start"]}

        # Clinical writes are blocked on completed encounters — open first.
        if desired_status == "completed":
            payload["status"] = "in_progress"

        encounter = base.create_encounter(
            patient_id,
            facility_id,
            organizations=org_ids,
            **payload,
        )
        encounter_id = encounter.id
        encounter_ids_by_ref[ref] = encounter_id
        patient_id_by_encounter_ref[ref] = patient_id
        period_start_by_encounter_ref[ref] = period["start"]

        if desired_status == "completed":
            close_after.append(
                {
                    "id": encounter_id,
                    "status": "completed",
                    "encounter_class": payload["encounter_class"],
                    "priority": payload["priority"],
                    "period": period,
                }
            )

        bed_ref = entry.get("bed_ref")
        if bed_ref:
            location_id = foundation_resource_id_by_ref[bed_ref]
            base.associate_encounter_location(
                facility_id,
                location_id,
                encounter_id,
                start_datetime=payload["period"]["start"],
            )

    return (
        encounter_ids_by_ref,
        patient_id_by_encounter_ref,
        close_after,
        period_start_by_encounter_ref,
    )


def load_clinical_content(
    base,
    facility_id,
    encounter_ids_by_ref,
    patient_id_by_encounter_ref,
    product_knowledge_by_ref,
    period_start_by_encounter_ref,
    user_ids_by_ref,
    close_after=None,
):
    """Upsert symptoms/diagnoses/meds, submit forms, apply service requests."""
    pack = load_json("clinical_content")
    requester_id = str(base.user.external_id)

    for entry in pack.get("symptoms", []):
        patient_id, encounter_id = _resolve_patient_and_encounter(
            entry, encounter_ids_by_ref, patient_id_by_encounter_ref
        )
        period_start = period_start_by_encounter_ref[entry["encounter_ref"]]
        created_date = _parse_period_start(period_start)
        datapoint = {
            key: value for key, value in entry.items() if key not in _CONDITION_ROW_META
        }
        datapoint.setdefault("clinical_status", "active")
        datapoint.setdefault("verification_status", "confirmed")
        datapoint.setdefault("category", "problem_list_item")
        datapoint["onset"] = _onset_for_entry(entry, period_start)
        datapoint["encounter"] = encounter_id
        base.upsert_symptoms(patient_id, [datapoint], created_date=created_date)

    for entry in pack.get("diagnoses", []):
        patient_id, encounter_id = _resolve_patient_and_encounter(
            entry, encounter_ids_by_ref, patient_id_by_encounter_ref
        )
        period_start = period_start_by_encounter_ref[entry["encounter_ref"]]
        created_date = _parse_period_start(period_start)
        datapoint = {
            key: value for key, value in entry.items() if key not in _CONDITION_ROW_META
        }
        datapoint.setdefault("clinical_status", "active")
        datapoint.setdefault("verification_status", "confirmed")
        datapoint.setdefault("category", "encounter_diagnosis")
        datapoint["onset"] = _onset_for_entry(entry, period_start)
        datapoint["encounter"] = encounter_id
        base.upsert_diagnoses(patient_id, [datapoint], created_date=created_date)

    for entry in pack.get("medication_requests", []):
        patient_id, encounter_id = _resolve_patient_and_encounter(
            entry, encounter_ids_by_ref, patient_id_by_encounter_ref
        )
        period_start = period_start_by_encounter_ref[entry["encounter_ref"]]
        created_date = _parse_period_start(period_start)
        product_knowledge_id = product_knowledge_by_ref[entry["product_knowledge_ref"]][
            "id"
        ]
        datapoint = _medication_datapoint(
            entry,
            encounter_id,
            product_knowledge_id,
            requester_id,
            created_date.isoformat(),
        )
        base.upsert_medication_requests(
            patient_id, [datapoint], created_date=created_date
        )

    for entry in pack.get("questionnaire_responses", []):
        patient_id, encounter_id = _resolve_patient_and_encounter(
            entry, encounter_ids_by_ref, patient_id_by_encounter_ref
        )
        period_start = period_start_by_encounter_ref[entry["encounter_ref"]]
        base.submit_questionnaire(
            entry["questionnaire_slug"],
            {
                "resource_id": encounter_id,
                "patient": patient_id,
                "encounter": encounter_id,
                "results": entry["results"],
            },
            created_date=_parse_period_start(period_start),
        )

    for entry in pack.get("service_requests", []):
        encounter_id = encounter_ids_by_ref[entry["encounter_ref"]]
        requester = user_ids_by_ref[entry["requester_user_ref"]]
        service_request = {
            "status": entry.get("status", "active"),
            "intent": entry.get("intent", "order"),
            "priority": entry.get("priority", "routine"),
            "category": entry.get("category", "laboratory"),
            "requester": requester,
        }
        if entry.get("note"):
            service_request["note"] = entry["note"]
        base.apply_activity_definition(
            facility_id,
            {
                "activity_definition": facility_slug(
                    facility_id, entry["activity_definition_slug"]
                ),
                "encounter": encounter_id,
                "service_request": service_request,
            },
        )

    for spec in close_after or []:
        base.update_encounter(
            spec["id"],
            {
                "status": spec["status"],
                "encounter_class": spec["encounter_class"],
                "priority": spec["priority"],
                "period": spec["period"],
            },
        )


def _period_from_days_ago(days_ago: int, status: str) -> dict:
    start = timezone.now() - timedelta(days=days_ago)
    period = {"start": start.isoformat()}
    if status == "completed":
        period["end"] = (start + _COMPLETED_ENCOUNTER_DURATION).isoformat()
    return period


def _parse_period_start(value: str) -> datetime:
    parsed = parse_datetime(value)
    if parsed is None:
        parsed = datetime.fromisoformat(value)
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, UTC)
    return parsed


def _onset_for_entry(entry: dict, period_start: str) -> dict:
    """Onset relative to encounter start (matches history text, not 'now')."""
    if "onset" in entry:
        return entry["onset"]
    start = _parse_period_start(period_start)
    delta = timedelta(
        days=int(entry.get("onset_days_before", 3)),
        hours=int(entry.get("onset_hours_before", 0)),
    )
    return {"onset_datetime": (start - delta).isoformat()}


def _resolve_patient_and_encounter(
    entry, encounter_ids_by_ref, patient_id_by_encounter_ref
):
    encounter_ref = entry["encounter_ref"]
    return (
        patient_id_by_encounter_ref[encounter_ref],
        encounter_ids_by_ref[encounter_ref],
    )


def _medication_datapoint(
    entry,
    encounter_id,
    product_knowledge_id,
    requester_id,
    authored_on,
):
    prescription_id = f"{encounter_id}-{entry['ref']}"
    payload = {
        "do_not_perform": False,
        "dosage_instruction": [
            {
                "as_needed_boolean": False,
                "dose_and_rate": {
                    "type": "ordered",
                    "dose_quantity": {
                        "value": entry["dose_value"],
                        "unit": {
                            "code": entry["dose_unit_code"],
                            "display": entry["dose_unit_display"],
                            "system": "http://unitsofmeasure.org",
                        },
                    },
                },
                "timing": {
                    "repeat": {
                        "frequency": entry["frequency"],
                        "period": entry["period"],
                        "period_unit": entry["period_unit"],
                        "bounds_duration": {
                            "value": entry["duration_value"],
                            "unit": entry["duration_unit"],
                        },
                    },
                    "code": {
                        "code": entry["timing_code"],
                        "display": entry["timing_display"],
                        "system": (
                            "http://terminology.hl7.org/CodeSystem/v3-GTSAbbreviation"
                        ),
                    },
                },
                "text": entry["text"],
            }
        ],
        "requested_product": product_knowledge_id,
        "status": "active",
        "intent": "order",
        "priority": "routine",
        "category": entry["category"],
        "authored_on": authored_on,
        "requester": requester_id,
        "create_prescription": {
            "alternate_identifier": prescription_id,
        },
        "encounter": encounter_id,
    }
    if entry.get("note"):
        payload["note"] = entry["note"]
    return payload
