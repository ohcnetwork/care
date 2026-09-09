from care.fixtures.base import generate_phone_number
from care.fixtures.loaders.facility import geo_organization_id_for_facility
from care.fixtures.loaders.load import load_json

_PATIENT_ROW_META = frozenset({"ref", "geo_org_ref"})


def load_patients(base, facility_id, organization_ids_by_ref=None) -> dict[str, str]:
    organization_ids_by_ref = organization_ids_by_ref or {}
    pack = load_json("patients")
    default_geo_id = geo_organization_id_for_facility(base, facility_id)
    patient_ids_by_ref: dict[str, str] = {}

    for entry in pack.get("patients", []):
        ref = entry["ref"]
        geo_org_ref = entry.get("geo_org_ref")
        geo_organization_id = (
            organization_ids_by_ref[geo_org_ref] if geo_org_ref else default_geo_id
        )

        payload = {
            key: value for key, value in entry.items() if key not in _PATIENT_ROW_META
        }
        payload["phone_number"] = generate_phone_number()

        patient = base.create_patient(geo_organization_id, **payload)
        patient_ids_by_ref[ref] = str(patient.id)

    return patient_ids_by_ref
