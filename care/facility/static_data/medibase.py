import logging
from typing import TypedDict

from django.core.paginator import Paginator
from django.db.models import CharField, TextField, Value
from django.db.models.functions import Coalesce
from redis_om import Field, Migrator

from care.facility.models.prescription import MedibaseMedicine as MedibaseMedicineModel
from care.utils.static_data.models.base import BaseRedisModel

logger = logging.getLogger(__name__)


class MedibaseMedicineObject(TypedDict):
    id: str
    name: str
    type: str
    generic: str
    company: str
    contents: str
    cims_class: str
    atc_classification: str


class MedibaseMedicine(BaseRedisModel):
    id: str = Field(primary_key=True)
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
    logger.info("Loading Medibase Medicines into the redis cache...")

    medibase_objects = (
        MedibaseMedicineModel.objects.order_by("external_id")
        .annotate(
            generic_pretty=Coalesce("generic", Value(""), output_field=CharField()),
            company_pretty=Coalesce("company", Value(""), output_field=CharField()),
            contents_pretty=Coalesce("contents", Value(""), output_field=TextField()),
            cims_class_pretty=Coalesce(
                "cims_class", Value(""), output_field=CharField()
            ),
            atc_classification_pretty=Coalesce(
                "atc_classification", Value(""), output_field=TextField()
            ),
        )
        .values_list(
            "external_id",
            "name",
            "type",
            "generic_pretty",
            "company_pretty",
            "contents_pretty",
            "cims_class_pretty",
            "atc_classification_pretty",
        )
    )
    paginator = Paginator(medibase_objects, 5000)
    for page_number in paginator.page_range:
        for medicine in paginator.page(page_number).object_list:
            MedibaseMedicine(
                id=str(medicine[0]),
                name=medicine[1],
                type=medicine[2],
                generic=medicine[3],
                company=medicine[4],
                contents=medicine[5],
                cims_class=medicine[6],
                atc_classification=medicine[7],
                vec=f"{medicine[1]} {medicine[3]} {medicine[4]}",
            ).save()
    Migrator().run()
    logger.info("Medibase Medicines Loaded")
