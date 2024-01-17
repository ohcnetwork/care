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
    label: str = Field(index=True, full_text_search=True)
    chapter: str

    def get_representation(self) -> ICD11Object:
        return {
            "id": self.id,
            "label": self.label,
            "chapter": self.chapter,
        }


def load_icd11_diagnosis():
    print("Loading ICD11 Diagnosis into the redis cache...", end="", flush=True)

    icd_objs = ICD11Diagnosis.objects.order_by("id").values_list(
        "id", "label", "meta_chapter_short"
    )
    paginator = Paginator(icd_objs, 5000)
    for page_number in paginator.page_range:
        for diagnosis in paginator.page(page_number).object_list:
            if re.match(DISEASE_CODE_PATTERN, diagnosis[1]):
                ICD11(
                    id=diagnosis[0],
                    label=diagnosis[1],
                    chapter=diagnosis[3] or "",
                ).save()
    Migrator().run()
    print("Done")


def get_icd11_diagnosis_object_by_id(
    diagnosis_id: int, as_dict=False
) -> ICD11 | ICD11Object | None:
    try:
        diagnosis = ICD11.get(diagnosis_id)
        return diagnosis.get_representation() if as_dict else diagnosis
    except KeyError:
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
