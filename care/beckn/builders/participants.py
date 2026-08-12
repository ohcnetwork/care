"""NFH ``HealthParticipant`` construction for a Care patient.

Shared by the BPP callbacks (which echo the patient they resolved back to the
BAP) and the BAP's outbound ``confirm`` (which describes the patient it is
requesting care for). Only identifiers that mean something to the counterparty
are carried: the ABHA number is a network-wide identity, whereas the Care patient
id is meaningless off this instance and is never sent.
"""

from care.beckn.constants import HEALTH_PARTICIPANT_CONTEXT, PARTICIPANT_ROLE_PATIENT
from care.beckn.services.identifiers import get_patient_abha_value
from care.emr.resources.patient.spec import GenderChoices

PATIENT_GENDER_TO_NFH = {
    GenderChoices.male.value: "MALE",
    GenderChoices.female.value: "FEMALE",
    GenderChoices.transgender.value: "OTHER",
    GenderChoices.non_binary.value: "OTHER",
}


def patient_participant_attributes(patient) -> dict:
    """Build the NFH ``HealthParticipant`` attributes for a Care patient.

    Always carries the required JSON-LD envelope (``@context``/``@type``) so the
    participant validates against the network schema; gender, date of birth and
    ABHA ``healthIds`` are added only when the patient record provides them.
    """
    attributes = {
        "@context": HEALTH_PARTICIPANT_CONTEXT,
        "@type": "hpa:HealthParticipant",
        "participantRole": PARTICIPANT_ROLE_PATIENT,
    }
    nfh_gender = PATIENT_GENDER_TO_NFH.get(patient.gender)
    if nfh_gender:
        attributes["gender"] = nfh_gender
    if patient.date_of_birth:
        attributes["dateOfBirth"] = patient.date_of_birth.isoformat()
    abha_value = get_patient_abha_value(patient)
    if abha_value:
        attributes["healthIds"] = [{"system": "ABHA", "value": abha_value}]
    return attributes


def inject_patient_health_ids(contract: dict, patient) -> None:
    """Ensure the contract carries a schema-valid PATIENT participant.

    Callbacks may echo an inbound contract whose PATIENT participant is missing
    (or lacks the JSON-LD envelope / ABHA), so the stored patient details are
    merged into the existing participant or, when absent, appended as a fully
    populated one. No-op when the patient is unknown.
    """
    if patient is None:
        return

    attributes = patient_participant_attributes(patient)
    participants = contract.setdefault("participants", [])
    for participant in participants:
        existing = participant.setdefault("participantAttributes", {})
        if existing.get("participantRole") != PARTICIPANT_ROLE_PATIENT:
            continue
        for key, value in attributes.items():
            if key != "healthIds":
                existing.setdefault(key, value)
        new_health_ids = attributes.get("healthIds", [])
        if new_health_ids:
            health_ids = existing.setdefault("healthIds", [])
            if not any((h.get("system") or "").upper() == "ABHA" for h in health_ids):
                health_ids.extend(new_health_ids)
        return

    participants.append(
        {
            "id": f"participant-patient-{patient.external_id}",
            "descriptor": {"name": patient.name, "shortDesc": "Patient (Subject)"},
            "participantAttributes": attributes,
        }
    )
