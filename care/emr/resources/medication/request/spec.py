from datetime import datetime
from enum import Enum

from django.shortcuts import get_object_or_404
from pydantic import UUID4, BaseModel, Field, field_validator

from care.emr.models.encounter import Encounter
from care.emr.models.medication_request import MedicationRequest
from care.emr.registries.care_valueset.care_valueset import validate_valueset
from care.emr.resources.base import EMRResource
from care.emr.resources.common.coding import Coding
from care.emr.resources.medication.valueset.additional_instruction import (
    CARE_ADDITIONAL_INSTRUCTION_VALUESET,
)
from care.emr.resources.medication.valueset.administration_method import (
    CARE_ADMINISTRATION_METHOD_VALUESET,
)
from care.emr.resources.medication.valueset.as_needed_reason import (
    CARE_AS_NEEDED_REASON_VALUESET,
)
from care.emr.resources.medication.valueset.body_site import CARE_BODY_SITE_VALUESET
from care.emr.resources.medication.valueset.medication import CARE_MEDICATION_VALUESET
from care.emr.resources.medication.valueset.route import CARE_ROUTE_VALUESET
from care.emr.resources.user.spec import UserSpec
from care.users.models import User


class MedicationRequestStatus(str, Enum):
    active = "active"
    on_hold = "on_hold"
    ended = "ended"
    stopped = "stopped"
    completed = "completed"
    cancelled = "cancelled"
    entered_in_error = "entered_in_error"
    draft = "draft"
    unknown = "unknown"


class StatusReason(str, Enum):
    alt_choice = "altchoice"
    clarif = "clarif"
    drughigh = "drughigh"
    hospadm = "hospadm"
    labint = "labint"
    non_avail = "non_avail"
    preg = "preg"
    salg = "salg"
    sddi = "sddi"
    sdupther = "sdupther"
    sintol = "sintol"
    surg = "surg"
    washout = "washout"


class MedicationRequestIntent(str, Enum):
    proposal = "proposal"
    plan = "plan"
    order = "order"
    original_order = "original_order"
    reflex_order = "reflex_order"
    filler_order = "filler_order"
    instance_order = "instance_order"


class MedicationRequestPriority(str, Enum):
    routine = "routine"
    urgent = "urgent"
    asap = "asap"
    stat = "stat"


class MedicationRequestCategory(str, Enum):
    inpatient = "inpatient"
    outpatient = "outpatient"
    community = "community"
    discharge = "discharge"


class TimingUnit(str, Enum):
    s = "s"
    min = "min"
    h = "h"
    d = "d"
    wk = "wk"
    mo = "mo"
    a = "a"


class DoseType(str, Enum):
    ordered = "ordered"
    calculated = "calculated"


class DosageQuantity(BaseModel):
    value: float
    unit: Coding


class TimingQuantity(BaseModel):
    value: float
    unit: TimingUnit


class DoseRange(BaseModel):
    low: DosageQuantity
    high: DosageQuantity


class DoseAndRate(BaseModel):
    type: DoseType
    dose_range: DoseRange | None = None
    dose_quantity: DosageQuantity | None = None


class TimingRepeat(BaseModel):
    frequency: int
    period: float
    period_unit: TimingUnit
    bounds_duration: TimingQuantity


class Timing(BaseModel):
    repeat: TimingRepeat
    code: Coding


class DosageInstruction(BaseModel):
    sequence: int | None = None
    text: str | None = None
    additional_instruction: list[Coding] | None = Field(
        None, json_schema_extra={"slug": CARE_ADDITIONAL_INSTRUCTION_VALUESET.slug}
    )
    patient_instruction: str | None = None
    timing: Timing | None = None
    as_needed_boolean: bool
    as_needed_for: Coding | None = Field(
        None, json_schema_extra={"slug": CARE_AS_NEEDED_REASON_VALUESET.slug}
    )
    site: Coding | None = Field(
        None, json_schema_extra={"slug": CARE_BODY_SITE_VALUESET.slug}
    )
    route: Coding | None = Field(
        None, json_schema_extra={"slug": CARE_ROUTE_VALUESET.slug}
    )
    method: Coding | None = Field(
        None, json_schema_extra={"slug": CARE_ADMINISTRATION_METHOD_VALUESET.slug}
    )
    dose_and_rate: DoseAndRate | None = None
    max_dose_per_period: DoseRange | None = None

    @field_validator("additional_instruction")
    @classmethod
    def validate_additional_instruction(cls, codes):
        if not codes:
            return codes
        return [
            validate_valueset(
                "additional_instruction",
                cls.model_fields["additional_instruction"].json_schema_extra["slug"],
                code,
            )
            for code in codes
        ]

    @field_validator("site")
    @classmethod
    def validate_site(cls, code):
        if not code:
            return code
        return validate_valueset(
            "site",
            cls.model_fields["site"].json_schema_extra["slug"],
            code,
        )

    @field_validator("route")
    @classmethod
    def validate_route(cls, code):
        if not code:
            return code
        return validate_valueset(
            "route",
            cls.model_fields["route"].json_schema_extra["slug"],
            code,
        )

    @field_validator("method")
    @classmethod
    def validate_method(cls, code):
        if not code:
            return code
        return validate_valueset(
            "method",
            cls.model_fields["method"].json_schema_extra["slug"],
            code,
        )


class MedicationRequestResource(EMRResource):
    __model__ = MedicationRequest
    __exclude__ = ["patient", "encounter", "requester"]


class BaseMedicationRequestSpec(MedicationRequestResource):
    id: UUID4 = None

    status: MedicationRequestStatus

    status_reason: StatusReason | None = None

    intent: MedicationRequestIntent

    category: MedicationRequestCategory
    priority: MedicationRequestPriority

    do_not_perform: bool

    medication: Coding = Field(
        json_schema_extra={"slug": CARE_MEDICATION_VALUESET.slug},
    )

    encounter: UUID4

    dosage_instruction: list[DosageInstruction] = Field()
    authored_on: datetime

    note: str | None = Field(None)


class MedicationRequestSpec(BaseMedicationRequestSpec):
    requester: UUID4 | None = None

    @field_validator("encounter")
    @classmethod
    def validate_encounter_exists(cls, encounter):
        if not Encounter.objects.filter(external_id=encounter).exists():
            err = "Encounter not found"
            raise ValueError(err)
        return encounter

    @field_validator("medication")
    @classmethod
    def validate_medication(cls, code):
        return validate_valueset(
            "medication",
            cls.model_fields["medication"].json_schema_extra["slug"],
            code,
        )

    def perform_extra_deserialization(self, is_update, obj):
        obj.encounter = Encounter.objects.get(external_id=self.encounter)
        obj.patient = obj.encounter.patient
        if self.requester:
            obj.requester = get_object_or_404(User, external_id=self.requester)


class MedicationRequestUpdateSpec(MedicationRequestResource):
    status: MedicationRequestStatus
    note: str | None = None


class MedicationRequestReadSpec(BaseMedicationRequestSpec):
    created_by: UserSpec = dict
    updated_by: UserSpec = dict
    created_date: datetime
    modified_date: datetime

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["encounter"] = obj.encounter.external_id

        if obj.created_by:
            mapping["created_by"] = UserSpec.serialize(obj.created_by)
        if obj.updated_by:
            mapping["updated_by"] = UserSpec.serialize(obj.updated_by)
