"""Patient resolution for inbound NFH referrals.

On ``init`` the BPP extracts the PATIENT participant from the contract and
reuses an existing Care ``Patient`` when one can be matched by health id
(ABHA), otherwise creates a new one. Required Care fields that the NFH
participant does not carry (phone number, geo organization) are backfilled
from the originating facility.
"""

from care.beckn.config import get_default_geo_organization
from care.beckn.mappers import (
    extract_dob_and_age,
    extract_health_ids,
    map_gender,
)
from care.beckn.services.identifiers import (
    attach_abha_identifier,
    find_patient_by_abha,
)
from care.emr.models import Patient

# A non-empty placeholder phone is required because Care's Patient model
# carries a phone number; emergency/unidentified referrals may omit it.
PLACEHOLDER_PHONE_NUMBER = "0000000000"


def _match_existing_patient(health_ids: list[dict]):
    """Reuse an existing patient by ABHA identifier.

    Phone-number matching is intentionally omitted: the Beckn network spec does
    not currently carry a patient phone number, so it is never a real value.
    """
    return find_patient_by_abha(health_ids)


def _patient_from_linked_referral(message: dict):
    """Return the patient already recorded on the referral this payload names.

    A downstream booking (T2) carries ``coordinationRef`` pointing at the
    referral (T1) it fulfils, and a referral that is being amended carries its
    own ``coordinationId``. Either way the patient is already on record, so
    reusing it keeps an ABHA-less patient from being created twice.
    """
    from care.beckn.mappers import get_coordination_ref
    from care.beckn.services.lookup import find_resource_request_by_coordination_id

    referral = find_resource_request_by_coordination_id(get_coordination_ref(message))
    if referral is None or not referral.related_patient_id:
        return None
    return referral.related_patient


def _match_patient_by_name_and_dob(participant: dict, facility):
    """Match a patient on name and date of birth within the facility's area.

    The last resort for a referral with no ABHA and no referral to inherit from.
    Both a name and a date of birth are required, and the search is confined to
    the originating facility's geo organization, so this cannot merge two people
    who merely share a name.
    """
    descriptor = participant.get("descriptor", {}) or {}
    name = (descriptor.get("name") or "").strip()
    date_of_birth, _age = extract_dob_and_age(participant)
    geo_organization = get_default_geo_organization(facility)
    if not (name and date_of_birth and geo_organization):
        return None
    return Patient.objects.filter(
        name__iexact=name,
        date_of_birth=date_of_birth,
        geo_organization=geo_organization,
    ).first()


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
    """Return an existing or newly created Care patient for the referral.

    Matched by ABHA where one is carried; failing that by the referral the
    payload belongs to, then by name and date of birth within the originating
    facility's area. Only when none of those resolve is a patient created.
    """
    if not participant:
        return None

    descriptor = participant.get("descriptor", {}) or {}
    name = descriptor.get("name") or "Unidentified Patient"
    attributes = participant.get("participantAttributes", {}) or {}
    health_ids = extract_health_ids(participant)
    phone_number = resolve_subject_phone(message, participant)

    existing = (
        _match_existing_patient(health_ids)
        or _patient_from_linked_referral(message)
        or _match_patient_by_name_and_dob(participant, facility)
    )
    if existing:
        # Keep the ABHA identifier in sync on reuse.
        attach_abha_identifier(existing, health_ids)
        return existing

    date_of_birth, _age = extract_dob_and_age(participant)

    patient = Patient(
        name=name,
        gender=map_gender(attributes.get("gender")),
        phone_number=phone_number,
        date_of_birth=date_of_birth,
        geo_organization=get_default_geo_organization(facility),
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
    attach_abha_identifier(patient, health_ids)
    return patient
