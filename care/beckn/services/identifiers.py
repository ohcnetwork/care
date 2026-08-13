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
    """Create/update ``PatientIdentifier`` rows for the patient's health ids.

    Also rebuilds ``Patient.instance_identifiers`` so the Care API/UI (which
    reads that JSON, not the identifier table) shows the health ids. This
    matters on confirm, when the patient was already created at init without
    them — and on a later confirm if the rows exist but the JSON is still
    empty.
    """
    touched = False
    for item in health_ids or []:
        value = item.get("value")
        if not value:
            continue
        touched = True
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
    if touched:
        patient.build_instance_identifiers()
        patient.save()


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
