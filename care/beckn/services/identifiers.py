"""Patient identifier configs for NFH health ids (ABHA, HFR, MRN, ...).

NFH participants carry ``healthIds`` ({system, value}). These are persisted as
proper Care ``PatientIdentifier`` rows (not just ``instance_identifiers`` JSON)
so they are queryable and usable for patient lookup. An instance-level
``PatientIdentifierConfig`` is auto-created per health-id system on first use.
"""

from care.emr.models.patient import PatientIdentifier, PatientIdentifierConfig
from care.emr.resources.patient_identifier.spec import (
    IdentifierConfig,
    PatientIdentifierStatus,
    PatientIdentifierUse,
)

# Health-id system -> identifier system slug + display.
HEALTH_ID_SYSTEMS = {
    "ABHA": ("system.care.ohc.network/abha-number", "ABHA Number"),
    "HFR": ("system.care.ohc.network/hfr-id", "HFR ID"),
    "MRN": ("system.care.ohc.network/mrn", "Medical Record Number"),
}

# Instance-level identifier system for the ABHA number recorded on ``on_confirm``.
# The ``official`` config is created on first use so upcoming bookings record the
# ABHA number and can be matched back to an existing patient.
ABHA_IDENTIFIER_SYSTEM = "care.ohc.network/patient-abha-number"

_CONFIG_CACHE: dict[str, PatientIdentifierConfig] = {}


def _system_slug(system: str) -> tuple[str, str]:
    key = (system or "").upper()
    if key in HEALTH_ID_SYSTEMS:
        return HEALTH_ID_SYSTEMS[key]
    slug = (system or "external").strip().lower().replace(" ", "-")
    return f"system.care.ohc.network/{slug}", system or "External Identifier"


def _get_or_create_config(system_slug: str, display: str) -> PatientIdentifierConfig:
    """Return the instance-level identifier config for a health-id system."""
    if system_slug in _CONFIG_CACHE:
        return _CONFIG_CACHE[system_slug]
    config = PatientIdentifierConfig.objects.filter(
        facility__isnull=True, config__system=system_slug
    ).first()
    if not config:
        config = PatientIdentifierConfig.objects.create(
            facility=None,
            status=PatientIdentifierStatus.active.value,
            config=IdentifierConfig(
                use=PatientIdentifierUse.secondary,
                system=system_slug,
                required=False,
                unique=False,
                regex="",
                display=display,
                auto_maintained=True,
            ).model_dump(mode="json"),
        )
    _CONFIG_CACHE[system_slug] = config
    return config


def upsert_health_id_identifiers(patient, health_ids: list[dict]) -> None:
    """Create/update ``PatientIdentifier`` rows for the patient's health ids."""
    for item in health_ids or []:
        value = item.get("value")
        if not value:
            continue
        system_slug, display = _system_slug(item.get("system"))
        config = _get_or_create_config(system_slug, display)
        existing = PatientIdentifier.objects.filter(
            patient=patient, config=config
        ).first()
        if existing:
            if existing.value != value:
                existing.value = value
                existing.save()
        else:
            PatientIdentifier.objects.create(
                patient=patient, config=config, value=value
            )


def build_instance_identifiers(health_ids: list[dict]) -> list[dict]:
    """Return ``Patient.instance_identifiers`` entries for the health ids.

    The patient serializer expects ``{"config": <config external_id>, "value"}``
    entries (it resolves the config via ``PatientIdentifierConfigCache``), so the
    raw ``{system, value}`` health ids must be converted to that shape.
    """
    entries = []
    for item in health_ids or []:
        value = item.get("value")
        if not value:
            continue
        system_slug, display = _system_slug(item.get("system"))
        config = _get_or_create_config(system_slug, display)
        entries.append({"config": str(config.external_id), "value": value})
    return entries


def _extract_abha_value(health_ids: list[dict]) -> str | None:
    """Return the ABHA number from a list of ``healthIds`` ({system, value})."""
    for item in health_ids or []:
        value = item.get("value")
        if value and (item.get("system") or "").upper() == "ABHA":
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

    The ``official`` ABHA identifier config is created on first use. If the
    patient already has an ABHA identifier it is reused (and refreshed when the
    value changed); otherwise a new one is created.
    """
    if patient is None:
        return None
    abha_value = _extract_abha_value(health_ids)
    if not abha_value:
        return None

    config = _get_or_create_abha_config()
    existing = PatientIdentifier.objects.filter(patient=patient, config=config).first()
    if existing:
        if existing.value != abha_value:
            existing.value = abha_value
            existing.save(update_fields=["value", "modified_date"])
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


def find_patient_by_health_ids(health_ids: list[dict]):
    """Return a patient matching any health id by identifier system + value."""
    for item in health_ids or []:
        value = item.get("value")
        if not value:
            continue
        system_slug, _ = _system_slug(item.get("system"))
        identifier = (
            PatientIdentifier.objects.filter(
                value=value, config__config__system=system_slug
            )
            .select_related("patient")
            .first()
        )
        if identifier:
            return identifier.patient
    return None
