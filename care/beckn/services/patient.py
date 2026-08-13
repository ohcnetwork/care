"""Patient resolution for inbound NFH referrals.

On ``init`` the BPP extracts the PATIENT participant from the contract and
reuses an existing Care ``Patient`` when one can be matched (by ABHA health id
or phone number), otherwise creates a new one. Required Care fields that the
NFH participant does not carry (phone number, geo organization) are backfilled
from the originating facility.
"""

from django.utils import timezone

from care.beckn.config import get_default_geo_organization
from care.beckn.mappers import (
    extract_dob_and_age,
    extract_health_ids,
    map_gender,
)
from care.beckn.services.identifiers import (
    build_instance_identifiers,
    find_patient_by_health_ids,
    upsert_health_id_identifiers,
)
from care.emr.models import Patient

# A non-empty placeholder phone is required because Care's Patient model
# carries a phone number; emergency/unidentified referrals may omit it.
PLACEHOLDER_PHONE_NUMBER = "0000000000"
# Referrals without a date of birth are recorded as this age.
DEFAULT_REFERRAL_AGE_YEARS = 35


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


def _match_by_demographics(name: str, gender, date_of_birth):
    """Reuse an existing patient by exact name, narrowed by DOB and gender.

    Used only when no health id / phone is available, to avoid duplicating the
    same person on re-referral. DOB and gender filters are applied only when the
    referral carries them.
    """
    queryset = Patient.objects.filter(name__iexact=name)
    if date_of_birth is not None:
        queryset = queryset.filter(date_of_birth=date_of_birth)
    if gender:
        queryset = queryset.filter(gender=gender)
    return queryset.first()


def _phone_from_contacts(contacts) -> str | None:
    """Return a phone value from a list of Beckn ``contacts``/``telecom`` items."""
    for contact in contacts or []:
        if not isinstance(contact, dict):
            continue
        system = (contact.get("system") or contact.get("type") or "").lower()
        value = contact.get("value") or contact.get("phone") or contact.get("number")
        if value and (system in {"phone", "mobile", "sms", "tel", ""} or not system):
            return value
    return None


def resolve_subject_phone(message: dict, participant: dict | None) -> str:
    """Resolve a phone number for the patient.

    Checks, in order: an explicit phone on the participant attributes
    (``phone``/``phoneNumber``/``telecom``/``contacts``), the participant
    ``descriptor``/``contacts`` (Beckn core), and finally the notification
    roster SMS channel for the SUBJECT party. Falls back to a placeholder.
    """
    from care.beckn.mappers import get_contract_attributes

    participant = participant or {}
    attributes = participant.get("participantAttributes", {}) or {}
    descriptor = participant.get("descriptor", {}) or {}

    explicit = (
        attributes.get("phone")
        or attributes.get("phoneNumber")
        or descriptor.get("phone")
        or descriptor.get("phoneNumber")
        or _phone_from_contacts(attributes.get("telecom"))
        or _phone_from_contacts(attributes.get("contacts"))
        or _phone_from_contacts(participant.get("contacts"))
    )
    if explicit:
        digits = str(explicit).strip()
        if digits:
            return digits[-14:]

    contract_attributes = get_contract_attributes(message)
    roster = contract_attributes.get("notificationRoster", []) or []
    participant_id = participant.get("id")
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

    date_of_birth, _age = extract_dob_and_age(participant)
    gender = map_gender(attributes.get("gender"))
    year_of_birth = None
    if date_of_birth is None:
        year_of_birth = timezone.now().year - DEFAULT_REFERRAL_AGE_YEARS
    # Demographics-only referrals (no health id / phone) still dedupe on the
    # patient's name (+ DOB / gender when present) so the same person is reused.
    if existing is None and name and name != "Unidentified Patient":
        existing = _match_by_demographics(name, gender, date_of_birth)
    if existing:
        # Keep identifiers in sync on reuse (e.g. a new health id arrived).
        upsert_health_id_identifiers(existing, health_ids)
        return existing

    patient = Patient(
        name=name,
        gender=gender,
        phone_number=phone_number,
        date_of_birth=date_of_birth,
        year_of_birth=year_of_birth,
        geo_organization=get_default_geo_organization(facility),
        instance_identifiers=build_instance_identifiers(health_ids),
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
