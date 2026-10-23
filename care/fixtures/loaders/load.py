import json
from pathlib import Path

DEFAULT_PACK = "generic_hospital_v1"


def pack_root(pack_name: str = DEFAULT_PACK) -> Path:
    return Path(__file__).resolve().parent.parent / "packs" / pack_name


def load_json(name: str, pack_name: str = DEFAULT_PACK):
    path = pack_root(pack_name) / f"{name}.json"
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def facility_slug(facility_id, slug_value: str) -> str:
    """Build a facility-scoped slug: ``f-{facility_id}-{slug_value}``."""
    return f"f-{facility_id}-{slug_value}"
