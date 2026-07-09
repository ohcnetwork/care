"""ABHA patient identifier handling for NFH bookings/referrals.

NFH participants carry ``healthIds`` ({system, value}). Only the ABHA number is
persisted as a Care ``PatientIdentifier`` row, under a dedicated instance-level
``official`` ``PatientIdentifierConfig`` that is created on first use.
"""

from care.emr.models.patient import PatientIdentifier, PatientIdentifierConfig
from care.emr.resources.patient_identifier.spec import (
    IdentifierConfig,
    PatientIdentifierStatus,
    PatientIdentifierUse,
)

# Instance-level identifier system for the ABHA number (use ``official``). The
# config is created on first use so upcoming bookings record the ABHA number and
# can be matched back to an existing patient.
ABHA_IDENTIFIER_SYSTEM = "care.ohc.network/patient-abha-number"

_CONFIG_CACHE: dict[str, PatientIdentifierConfig] = {}


def _is_abha(system: str) -> bool:
    return (system or "").upper() == "ABHA"


def _extract_abha_value(health_ids: list[dict]) -> str | None:
    """Return the ABHA number from a list of ``healthIds`` ({system, value})."""
    for item in health_ids or []:
        value = item.get("value")
        if value and _is_abha(item.get("system")):
            return value
    return None


def _get_or_create_abha_config() -> PatientIdentifierConfig:
    """Return the instance-level ABHA (``official``) identifier config.

    Created on first use so upcoming bookings can record the ABHA number
    without a manual/migration setup step.
    """
    if ABHA_IDENTIFIER_SYSTEM in _CONFIG_CACHE:
        return _CONFIG_CACHE[ABHA_IDENTIFIER_SYSTEM]
    config = PatientIdentifierConfig.objects.filter(
        facility__isnull=True, config__system=ABHA_IDENTIFIER_SYSTEM
    ).first()
    if not config:
        config = PatientIdentifierConfig.objects.create(
            facility=None,
            status=PatientIdentifierStatus.active.value,
            config=IdentifierConfig(
                use=PatientIdentifierUse.official,
                system=ABHA_IDENTIFIER_SYSTEM,
                required=False,
                unique=False,
                regex="",
                display="ABHA Number",
                auto_maintained=True,
            ).model_dump(mode="json"),
        )
    _CONFIG_CACHE[ABHA_IDENTIFIER_SYSTEM] = config
    return config


def attach_abha_identifier(patient, health_ids: list[dict]) -> PatientIdentifier | None:
    """Attach the ABHA number as a ``PatientIdentifier`` on the patient.

    The ``official`` ABHA identifier config is created on first use. The patient
    is searched for an ABHA identifier carrying this exact value; if one is not
    already present, a new identifier is created.
    """
    if patient is None:
        return None
    abha_value = _extract_abha_value(health_ids)
    if not abha_value:
        return None

    config = _get_or_create_abha_config()
    existing = PatientIdentifier.objects.filter(
        patient=patient, config=config, value=abha_value
    ).first()
    if existing:
        return existing
    return PatientIdentifier.objects.create(
        patient=patient, config=config, value=abha_value
    )


def find_patient_by_abha(health_ids: list[dict]):
    """Return an existing patient carrying the ABHA number, if any."""
    abha_value = _extract_abha_value(health_ids)
    if not abha_value:
        return None
    identifier = (
        PatientIdentifier.objects.filter(
            value=abha_value, config__config__system=ABHA_IDENTIFIER_SYSTEM
        )
        .select_related("patient")
        .first()
    )
    return identifier.patient if identifier else None


def get_patient_abha_value(patient) -> str | None:
    """Return the patient's stored ABHA number, if an identifier exists."""
    if patient is None:
        return None
    identifier = PatientIdentifier.objects.filter(
        patient=patient, config__config__system=ABHA_IDENTIFIER_SYSTEM
    ).first()
    return identifier.value if identifier else None
