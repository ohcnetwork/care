"""Patient resolution for inbound NFH referrals.

On ``init`` the BPP extracts the PATIENT participant from the contract and
reuses an existing Care ``Patient`` when one can be matched (by ABHA health id
or phone number), otherwise creates a new one. Required Care fields that the
NFH participant does not carry (phone number, geo organization) are backfilled
from the originating facility.
"""

from care.beckn.config import get_default_geo_organization
from care.beckn.mappers import (
    extract_dob_and_age,
    extract_health_ids,
    map_gender,
)
from care.beckn.services.identifiers import (
    find_patient_by_health_ids,
    upsert_health_id_identifiers,
)
from care.emr.models import Patient

# A non-empty placeholder phone is required because Care's Patient model
# carries a phone number; emergency/unidentified referrals may omit it.
PLACEHOLDER_PHONE_NUMBER = "0000000000"


def _match_existing_patient(health_ids: list[dict], phone_number: str | None):
    """Reuse an existing patient by health-id identifier, then by phone."""
    patient = find_patient_by_health_ids(health_ids)
    if patient:
        return patient

    if phone_number and phone_number != PLACEHOLDER_PHONE_NUMBER:
        patient = Patient.objects.filter(phone_number=phone_number).first()
        if patient:
            return patient
    return None


def resolve_subject_phone(message: dict, participant: dict | None) -> str:
    """Resolve a phone number for the patient.

    Prefers an explicit phone on the participant (``phone``/``telecom``), then
    the notification roster SMS channel for the SUBJECT party.
    """
    from care.beckn.mappers import get_contract_attributes

    attributes = (participant or {}).get("participantAttributes", {}) or {}
    explicit = attributes.get("phone") or attributes.get("phoneNumber")
    if not explicit:
        for telecom in attributes.get("telecom", []) or []:
            if (telecom.get("system") or "").lower() == "phone" and telecom.get(
                "value"
            ):
                explicit = telecom["value"]
                break
    if explicit:
        digits = str(explicit).strip()
        if digits:
            return digits[-14:]

    contract_attributes = get_contract_attributes(message)
    roster = contract_attributes.get("notificationRoster", []) or []
    participant_id = (participant or {}).get("id")
    for entry in roster:
        channel = entry.get("channelRef", "") or ""
        if not channel.startswith("sms:"):
            continue
        if (
            entry.get("partyRole") == "SUBJECT"
            or entry.get("partyRef") == participant_id
        ):
            number = channel.split("sms:", 1)[1].strip()
            if number:
                return number[-14:]
    return PLACEHOLDER_PHONE_NUMBER


def find_or_create_patient(message: dict, participant: dict | None, facility, user):
    """Return an existing or newly created Care patient for the referral."""
    if not participant:
        return None

    descriptor = participant.get("descriptor", {}) or {}
    name = descriptor.get("name") or "Unidentified Patient"
    attributes = participant.get("participantAttributes", {}) or {}
    health_ids = extract_health_ids(participant)
    phone_number = resolve_subject_phone(message, participant)

    existing = _match_existing_patient(health_ids, phone_number)
    if existing:
        # Keep identifiers in sync on reuse (e.g. a new health id arrived).
        upsert_health_id_identifiers(existing, health_ids)
        return existing

    date_of_birth, _age = extract_dob_and_age(participant)

    patient = Patient(
        name=name,
        gender=map_gender(attributes.get("gender")),
        phone_number=phone_number,
        date_of_birth=date_of_birth,
        geo_organization=get_default_geo_organization(facility),
        instance_identifiers=health_ids,
        created_by=user,
        updated_by=user,
    )
    patient.extensions = {
        "beckn": {
            "primaryLanguage": attributes.get("primaryLanguage"),
            "participant": participant,
        }
    }
    patient.save()
    upsert_health_id_identifiers(patient, health_ids)
    return patient
