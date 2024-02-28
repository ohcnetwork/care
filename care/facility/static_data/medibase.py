import json
from typing import TypedDict

from redis_om import Field, Migrator

from care.utils.static_data.models.base import BaseRedisModel


class MedibaseMedicineObject(TypedDict):
    id: int
    name: str
    type: str
    generic: str
    company: str
    contents: str
    cims_class: str
    atc_classification: str


class MedibaseMedicine(BaseRedisModel):
    id: int = Field(primary_key=True)
    name: str = Field(index=True)
    type: str = Field(index=True)
    generic: str
    company: str
    contents: str
    cims_class: str
    atc_classification: str

    vec: str = Field(index=True, full_text_search=True)

    def get_representation(self) -> MedibaseMedicineObject:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "generic": self.generic,
            "company": self.company,
            "contents": self.contents,
            "cims_class": self.cims_class,
            "atc_classification": self.atc_classification,
        }


def load_medibase_medicines():
    print("Loading Medibase Medicines into the redis cache...", end="", flush=True)

    with open("data/medibase.json", "r") as f:
        medibase_data = json.load(f)

    for medicine in medibase_data:
        MedibaseMedicine(
            id=medicine.get("id"),
            name=medicine.get("name", ""),
            type=medicine.get("type", ""),
            generic=medicine.get("generic", ""),
            company=medicine.get("company", ""),
            contents=medicine.get("contents", ""),
            cims_class=medicine.get("cims_class", ""),
            atc_classification=medicine.get("atc_classification", ""),
            vec=f"{medicine.get('name', '')} {medicine.get('generic', '')} {medicine.get('company', '')}",
        ).save()
    Migrator().run()
    print("Done")
