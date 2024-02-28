import json
import re
from typing import TypedDict

from redis_om import Field, Migrator
from redis_om.model.model import NotFoundError as RedisModelNotFoundError

from care.facility.management.commands.load_icd11_diagnoses_data import icd11_id_to_int
from care.utils.static_data.models.base import BaseRedisModel

DISEASE_CODE_PATTERN = r"^(?:[A-Z]+\d|\d+[A-Z])[A-Z\d.]*\s"


class ICD11Object(TypedDict):
    id: int
    label: str
    chapter: str


class ICD11(BaseRedisModel):
    id: int = Field(primary_key=True)
    label: str = Field(index=True, full_text_search=True)
    chapter: str
    has_code: int = Field(index=True)

    def get_representation(self) -> ICD11Object:
        return {
            "id": self.id,
            "label": self.label,
            "chapter": self.chapter,
        }


def load_icd11_diagnosis():
    print("Loading ICD11 Diagnosis into the redis cache...", end="", flush=True)

    with open("data/icd11.json", "r") as f:
        icd_data = json.load(f)
    for diagnosis in icd_data:
        ICD11(
            id=icd11_id_to_int(diagnosis.get("ID")),
            label=diagnosis.get("label"),
            chapter=diagnosis.get("meta_chapter_short", ""),
            has_code=1 if re.match(DISEASE_CODE_PATTERN, diagnosis.get("label")) else 0,
        ).save()
    Migrator().run()
    print("Done")


def get_icd11_diagnosis_object_by_id(
    diagnosis_id: int, as_dict=False
) -> ICD11 | ICD11Object | None:
    try:
        diagnosis = ICD11.get(diagnosis_id)
        return diagnosis.get_representation() if as_dict else diagnosis
    except RedisModelNotFoundError:
        return None


def get_icd11_diagnoses_objects_by_ids(diagnoses_ids: list[int]) -> list[ICD11Object]:
    if not diagnoses_ids:
        return []

    query = None
    for diagnosis_id in diagnoses_ids:
        if query is None:
            query = ICD11.id == diagnosis_id
        else:
            query |= ICD11.id == diagnosis_id

    diagnosis_objects: list[ICD11] = list(ICD11.find(query))
    return [diagnosis.get_representation() for diagnosis in diagnosis_objects]
