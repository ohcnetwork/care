from datetime import datetime
from enum import Enum

from pydantic import UUID4, BaseModel, Field, field_validator

from care.emr.fhir.schema.base import Coding
from care.emr.models.encounter import Encounter
from care.emr.models.medication_request import MedicationRequest
from care.emr.registries.care_valueset.care_valueset import validate_valueset
from care.emr.resources.base import EMRResource
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
    unit: str


class DoseRange(BaseModel):
    low: DosageQuantity
    high: DosageQuantity


class DoseAndRate(BaseModel):
    type: DoseType | None = None
    dose_range: DoseRange | None = None
    dose_quantity: DosageQuantity | None = None


class TimingRepeat(BaseModel):
    frequency: int | None = None
    period: float | None = None
    period_unit: TimingUnit
    bounds_duration: DosageQuantity | None = None


class Timing(BaseModel):
    repeat: TimingRepeat | None = None
    code: Coding | None = None


class DosageInstruction(BaseModel):
    sequence: int | None = None
    text: str | None = None
    additional_instruction: list[Coding] | None = Field(
        None, json_schema_extra={"slug": CARE_ADDITIONAL_INSTRUCTION_VALUESET.slug}
    )
    patient_instruction: str | None = None
    timing: Timing | None = None
    as_needed_boolean: bool | None = None
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


class BaseMedicationRequestSpec(EMRResource):
    __model__ = MedicationRequest
    __exclude__ = ["patient", "encounter"]
    id: UUID4 = None

    status: MedicationRequestStatus = Field(
        description="Status of the medication request",
    )

    status_reason: StatusReason | None = Field(
        None, description="Reason for current status"
    )

    status_changed: datetime = None

    intent: MedicationRequestIntent = Field(
        description="Whether this is a proposal, plan, original order, etc.",
    )

    category: MedicationRequestCategory = Field(
        description="Context of medication request",
    )
    priority: MedicationRequestPriority = Field(
        description="Urgency of the request",
    )

    do_not_perform: bool = Field(
        description="True if medication is NOT to be given",
    )

    medication: Coding = Field(
        description="Medication requested, using SNOMED CT coding",
        json_schema_extra={"slug": CARE_MEDICATION_VALUESET.slug},
    )

    encounter: UUID4 = Field(description="Encounter during which request was created")

    authored_on: datetime = Field(
        description="When request was initially authored",
    )

    dosage_instruction: list[DosageInstruction] = Field(
        description="Dosage instructions for the medication",
    )

    note: str | None = Field(None, description="Additional notes about the request")


class MedicationRequestSpec(BaseMedicationRequestSpec):
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
        if not is_update:
            obj.encounter = Encounter.objects.get(
                external_id=self.encounter
            )  # Needs more validation
            obj.patient = obj.encounter.patient


class MedicationRequestReadSpec(BaseMedicationRequestSpec):
    created_by: UserSpec = dict
    updated_by: UserSpec = dict

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["encounter"] = obj.encounter.external_id

        if obj.created_by:
            mapping["created_by"] = UserSpec.serialize(obj.created_by)
        if obj.updated_by:
            mapping["updated_by"] = UserSpec.serialize(obj.updated_by)


class MedicationRequestDiscontinueRequest(BaseModel):
    status_reason: StatusReason = Field(description="Reason for discontinuation")
