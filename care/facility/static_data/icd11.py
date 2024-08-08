import re
from typing import TypedDict

from django.core.paginator import Paginator
from redis_om import Field, Migrator

from care.facility.models.icd11_diagnosis import ICD11Diagnosis
from care.utils.static_data.models.base import BaseRedisModel

DISEASE_CODE_PATTERN = r"^(?:[A-Z]+\d|\d+[A-Z])[A-Z\d.]*\s"


class ICD11Object(TypedDict):
    id: int
    label: str
    chapter: str


class ICD11(BaseRedisModel):
    id: int = Field(primary_key=True)
    label: str
    chapter: str = Field(index=True)
    has_code: int = Field(index=True)

    vec: str = Field(index=True, full_text_search=True)

    def get_representation(self) -> ICD11Object:
        return {
            "id": self.id,
            "label": self.label,
            "chapter": self.chapter if self.chapter != "null" else "",
        }


def load_icd11_diagnosis():
    print("Loading ICD11 Diagnosis into the redis cache...", end="", flush=True)

    icd_objs = ICD11Diagnosis.objects.order_by("id").values_list(
        "id", "label", "meta_chapter_short"
    )
    paginator = Paginator(icd_objs, 5000)
    for page_number in paginator.page_range:
        for diagnosis in paginator.page(page_number).object_list:
            ICD11(
                id=diagnosis[0],
                label=diagnosis[1],
                chapter=diagnosis[2] or "null",
                has_code=1 if re.match(DISEASE_CODE_PATTERN, diagnosis[1]) else 0,
                vec=diagnosis[1].replace(".", "\\.", 1),
            ).save()
    Migrator().run()
    print("Done")


def get_icd11_diagnosis_object_by_id(
    diagnosis_id: int, as_dict=False
) -> ICD11 | ICD11Object | None:
    try:
        diagnosis = ICD11.get(diagnosis_id)
        return diagnosis.get_representation() if as_dict else diagnosis
    except Exception:
        return None


def get_icd11_diagnoses_objects_by_ids(diagnoses_ids: list[int]) -> list[ICD11Object]:
    if not diagnoses_ids:
        return []

    diagnoses_objects = []
    for diagnosis_id in diagnoses_ids:
        diagnoses = get_icd11_diagnosis_object_by_id(diagnosis_id)
        if diagnoses:
            diagnoses_objects.append(diagnoses)

    return diagnoses_objects
