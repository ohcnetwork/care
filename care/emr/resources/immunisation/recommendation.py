from datetime import date
from enum import Enum

from pydantic import UUID4, model_validator
from pydantic.experimental.missing_sentinel import MISSING
from pydantic_core.core_schema import ValidationInfo

from care.emr.models.encounter import Encounter
from care.emr.models.immunisation import ImmunizationRecommendation
from care.emr.models.patient import Patient
from care.emr.resources.base import EMRResource
from care.emr.resources.condition.valueset import CARE_CODITION_CODE_VALUESET
from care.emr.resources.medication.valueset.medication import CARE_MEDICATION_VALUESET
from care.emr.utils.valueset_coding_type import ValueSetBoundCoding
from care.utils.shortcuts import get_object_or_404


class ImmunizationRecommendationForecastStatus(str, Enum):
    due = "due"
    immune = "immune"
    contraindicated = "contraindicated"
    complete = "complete"
    # overdue omitted, due + due_date can be used to determine if it is overdue


class BaseImmunizationRecommendationSpec(EMRResource):
    """Base model for healthcare service"""

    __model__ = ImmunizationRecommendation

    id: UUID4 | None = None
    codes: list[ValueSetBoundCoding[CARE_MEDICATION_VALUESET.slug]] | MISSING = MISSING
    diseases: list[ValueSetBoundCoding[CARE_CODITION_CODE_VALUESET.slug]] | MISSING = (
        MISSING
    )
    due_date: date | MISSING = MISSING
    earliest_date: date | MISSING = MISSING
    overdue_date: date | MISSING = MISSING
    description: str | MISSING = MISSING
    series: str | MISSING = MISSING
    dose_number: str | MISSING = MISSING
    series_number: str | MISSING = MISSING


class ImmunizationRecommendationCreateSpec(BaseImmunizationRecommendationSpec):
    parent: UUID4 | None = None
    patient: UUID4
    encounter: UUID4 | None = None
    is_group: bool
    forecast_status: ImmunizationRecommendationForecastStatus

    @model_validator(mode="after")
    def validate_codes(self):
        if not self.is_group and self.codes is MISSING:
            raise ValueError("Codes are required for non-group recommendations")
        return self

    def perform_extra_deserialization(self, is_update, obj):
        obj.patient = get_object_or_404(
            Patient.objects.only("id"), external_id=self.patient
        )
        if self.parent:
            obj.parent = get_object_or_404(
                ImmunizationRecommendation.objects.filter(patient=obj.patient).only(
                    "id"
                ),
                external_id=self.parent,
            )
        if self.encounter:
            obj.encounter = get_object_or_404(
                Encounter.objects.filter(patient=obj.patient).only("id"),
                external_id=self.encounter,
            )
        return super().perform_extra_deserialization(is_update, obj)


class ImmunizationRecommendationUpdateSpec(BaseImmunizationRecommendationSpec):
    forecast_status: ImmunizationRecommendationForecastStatus

    @model_validator(mode="after")
    def validate_codes(self, info: ValidationInfo):
        obj = (info.context or {}).get("object")
        if obj is not None and not obj.is_group and self.codes is MISSING:
            raise ValueError("Codes are required for non-group recommendations")
        return self


class ImmunizationRecommendationListSpec(BaseImmunizationRecommendationSpec):
    forecast_status: ImmunizationRecommendationForecastStatus
    is_group: bool

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id


class ImmunizationRecommendationRetrieveSpec(ImmunizationRecommendationListSpec):
    pass
