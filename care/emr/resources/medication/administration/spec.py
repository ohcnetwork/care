from datetime import datetime
from enum import Enum

from pydantic import UUID4, BaseModel, Field, field_validator

from care.emr.models.encounter import Encounter
from care.emr.models.medication_administration import MedicationAdministration
from care.emr.models.medication_request import MedicationRequest
from care.emr.resources.base import EMRResource
from care.emr.resources.common import Quantity
from care.emr.resources.medication.valueset.administration_method import (
    CARE_ADMINISTRATION_METHOD_VALUESET,
)
from care.emr.resources.medication.valueset.body_site import CARE_BODY_SITE_VALUESET
from care.emr.resources.medication.valueset.medication import CARE_MEDICATION_VALUESET
from care.emr.resources.medication.valueset.route import CARE_ROUTE_VALUESET
from care.emr.resources.user.spec import UserSpec
from care.emr.utils.valueset_coding_type import ValueSetBoundCoding
from care.users.models import User


class MedicationAdministrationStatus(str, Enum):
    completed = "completed"
    not_done = "not_done"
    entered_in_error = "entered_in_error"
    stopped = "stopped"
    in_progress = "in_progress"
    on_hold = "on_hold"
    unknown = "unknown"
    cancelled = "cancelled"


class MedicationAdministrationCategory(str, Enum):
    inpatient = "inpatient"
    outpatient = "outpatient"
    community = "community"
    discharge = "discharge"


class MedicationAdministrationPerformerFunction(str, Enum):
    performer = "performer"
    verifier = "verifier"
    witness = "witness"


class MedicationAdministrationPerformer(BaseModel):
    actor: UUID4 = Field(
        description="The user who performed the administration",
    )
    function: MedicationAdministrationPerformerFunction | None = Field(
        description="The function of the performer",
    )

    @field_validator("actor")
    @classmethod
    def validate_actor_exists(cls, actor):
        if not User.objects.filter(external_id=actor).exists():
            err = "User not found"
            raise ValueError(err)
        return actor


class Dosage(BaseModel):
    text: str | None = Field(
        None,
        description="Free text dosage instructions",
    )
    site: ValueSetBoundCoding[CARE_BODY_SITE_VALUESET.slug] | None = None
    route: ValueSetBoundCoding[CARE_ROUTE_VALUESET.slug] | None = None
    method: ValueSetBoundCoding[CARE_ADMINISTRATION_METHOD_VALUESET.slug] | None = None
    dose: Quantity | None = Field(
        None,
        description="The amount of medication administered",
    )
    rate: Quantity | None = Field(
        None,
        description="The speed of administration",
    )


class BaseMedicationAdministrationSpec(EMRResource):
    __model__ = MedicationAdministration
    __exclude__ = ["patient", "encounter", "request"]
    id: UUID4 = None

    status: MedicationAdministrationStatus

    status_reason: ValueSetBoundCoding[CARE_MEDICATION_VALUESET.slug] | None = None
    category: MedicationAdministrationCategory | None = None

    medication: ValueSetBoundCoding[CARE_MEDICATION_VALUESET.slug]

    authored_on: datetime | None = Field(
        None,
        description="When request was initially authored",
    )
    occurrence_period_start: datetime = Field(
        description="When the medication was administration started",
    )
    occurrence_period_end: datetime | None = None

    recorded: datetime | None = Field(
        None,
        description="When administration was recorded",
    )

    encounter: UUID4 = Field(
        description="The encounter where the administration was noted",
    )
    request: UUID4 = Field(
        description="The medication request under which the administration was made",
    )

    performer: list[MedicationAdministrationPerformer] | None = Field(
        None,
        description="Who administered the medication",
    )
    dosage: Dosage | None = Field(
        None,
        description="The dosage of the medication",
    )

    note: str | None = None


class MedicationAdministrationSpec(BaseMedicationAdministrationSpec):
    @field_validator("encounter")
    @classmethod
    def validate_encounter_exists(cls, encounter):
        if not Encounter.objects.filter(external_id=encounter).exists():
            err = "Encounter not found"
            raise ValueError(err)
        return encounter

    @field_validator("request")
    @classmethod
    def validate_request(cls, request):
        if not MedicationRequest.objects.filter(external_id=request).exists():
            err = "Medication Request not found"
            raise ValueError(err)
        return request

    def perform_extra_deserialization(self, is_update, obj):
        if not is_update:
            obj.encounter = Encounter.objects.get(
                external_id=self.encounter
            )  # Needs more validation
            obj.patient = obj.encounter.patient
            obj.request = MedicationRequest.objects.get(external_id=self.request)


class MedicationAdministrationUpdateSpec(EMRResource):
    __model__ = MedicationAdministration
    __exclude__ = ["patient", "encounter", "request"]

    status: MedicationAdministrationStatus
    note: str | None = None
    occurrence_period_end: datetime | None = None


class MedicationAdministrationReadSpec(BaseMedicationAdministrationSpec):
    created_by: UserSpec = dict

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["encounter"] = obj.encounter.external_id
        mapping["request"] = obj.request.external_id

        if obj.created_by:
            mapping["created_by"] = UserSpec.serialize(obj.created_by)
