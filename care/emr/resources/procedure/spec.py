from datetime import datetime
from enum import Enum

from pydantic import (
    UUID4,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)
from pydantic.experimental.missing_sentinel import MISSING

from care.emr.models.encounter import Encounter
from care.emr.models.procedure import Procedure
from care.emr.resources.base import EMRResource, PeriodSpec
from care.emr.resources.common.coding import Coding
from care.emr.resources.medication.valueset.body_site import CARE_BODY_SITE_VALUESET
from care.emr.resources.procedure.valueset import (
    CARE_PROCEDURE_CATEGORY_VALUESET,
    CARE_PROCEDURE_CODE_VALUESET,
    CARE_PROCEDURE_REASON_VALUESET,
    CARE_PROCEDURE_STATUS_REASON_VALUESET,
)
from care.emr.utils.valueset_coding_type import ValueSetBoundCoding
from care.utils.time_util import care_now


class ProcedureStatus(str, Enum):
    completed = "completed"
    not_done = "not_done"
    stopped = "stopped"
    entered_in_error = "entered_in_error"
    unknown = "unknown"


class ProcedureOutcome(str, Enum):
    successful = "successful"
    unsuccessful = "unsuccessful"
    partially_successful = "partially_successful"


class ProcedureOccurrenceSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    occurrence_datetime: AwareDatetime | None = None
    occurrence_period: PeriodSpec | None = None
    occurrence_string: str | None = Field(default=None, min_length=1)

    @field_validator("occurrence_string")
    @classmethod
    def validate_occurrence_string(cls, value):
        if value is not None and not value.strip():
            raise ValueError("Occurrence description cannot be blank")
        return value

    @model_validator(mode="after")
    def validate_occurrence(self):
        choices = (
            self.occurrence_datetime,
            self.occurrence_period,
            self.occurrence_string,
        )
        if sum(value is not None for value in choices) > 1:
            raise ValueError("Only one occurrence type can be supplied")
        now = care_now()
        dates = [self.occurrence_datetime]
        if self.occurrence_period:
            dates.extend([self.occurrence_period.start, self.occurrence_period.end])
        if any(value and value > now for value in dates):
            raise ValueError("Procedure occurrence cannot be in the future")
        return self


class BaseProcedureSpec(EMRResource):
    __model__ = Procedure
    __exclude__ = ["patient", "encounter"]

    id: UUID4 | None = None


class ProcedureCreateSpec(BaseProcedureSpec):
    encounter: UUID4
    status: ProcedureStatus
    status_reason: (
        ValueSetBoundCoding[CARE_PROCEDURE_STATUS_REASON_VALUESET.slug] | None
    ) = None
    category: list[ValueSetBoundCoding[CARE_PROCEDURE_CATEGORY_VALUESET.slug]] = Field(
        default_factory=list
    )
    code: ValueSetBoundCoding[CARE_PROCEDURE_CODE_VALUESET.slug]
    occurrence: ProcedureOccurrenceSpec = Field(default_factory=ProcedureOccurrenceSpec)
    recorded_date: AwareDatetime | None = None
    body_site: list[ValueSetBoundCoding[CARE_BODY_SITE_VALUESET.slug]] = Field(
        default_factory=list
    )
    reason: list[ValueSetBoundCoding[CARE_PROCEDURE_REASON_VALUESET.slug]] = Field(
        default_factory=list
    )
    outcome: ProcedureOutcome | None = None
    note: str | None = None

    @field_validator("encounter")
    @classmethod
    def validate_encounter_exists(cls, encounter):
        if not Encounter.objects.filter(external_id=encounter).exists():
            raise ValueError("Encounter not found")
        return encounter

    def perform_extra_deserialization(self, is_update, obj):
        obj.encounter = Encounter.objects.get(external_id=self.encounter)
        obj.patient = obj.encounter.patient
        obj.is_primary_source = False


class ProcedureUpdateSpec(BaseProcedureSpec):
    status: ProcedureStatus | MISSING = MISSING
    status_reason: (
        ValueSetBoundCoding[CARE_PROCEDURE_STATUS_REASON_VALUESET.slug] | None | MISSING
    ) = MISSING
    category: (
        list[ValueSetBoundCoding[CARE_PROCEDURE_CATEGORY_VALUESET.slug]] | MISSING
    ) = MISSING
    code: ValueSetBoundCoding[CARE_PROCEDURE_CODE_VALUESET.slug] | MISSING = MISSING
    occurrence: ProcedureOccurrenceSpec | MISSING = MISSING
    recorded_date: AwareDatetime | None | MISSING = MISSING
    body_site: list[ValueSetBoundCoding[CARE_BODY_SITE_VALUESET.slug]] | MISSING = (
        MISSING
    )
    reason: list[ValueSetBoundCoding[CARE_PROCEDURE_REASON_VALUESET.slug]] | MISSING = (
        MISSING
    )
    outcome: ProcedureOutcome | None | MISSING = MISSING
    note: str | None | MISSING = MISSING


class ProcedureReadSpec(BaseProcedureSpec):
    status: ProcedureStatus
    status_reason: Coding | None = None
    category: list[Coding] = Field(default_factory=list)
    code: Coding
    occurrence: ProcedureOccurrenceSpec = Field(default_factory=ProcedureOccurrenceSpec)
    recorded_date: datetime | None = None
    is_primary_source: bool
    body_site: list[Coding] = Field(default_factory=list)
    reason: list[Coding] = Field(default_factory=list)
    outcome: ProcedureOutcome | None = None
    note: str | None = None

    created_date: datetime
    modified_date: datetime

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id


class ProcedureRetrieveSpec(ProcedureReadSpec):
    encounter: UUID4
    created_by: dict | None = None
    updated_by: dict | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        mapping["encounter"] = obj.encounter.external_id
        cls.serialize_audit_users(mapping, obj)
