from datetime import datetime
from enum import Enum

from pydantic import UUID4, Field, field_validator

from care.emr.fhir.schema.base import Coding, Period
from care.emr.models.encounter import Encounter
from care.emr.models.medication_statement import MedicationStatement
from care.emr.registries.care_valueset.care_valueset import validate_valueset
from care.emr.resources.base import EMRResource
from care.emr.resources.medication.valueset.medication import CARE_MEDICATION_VALUESET
from care.emr.resources.user.spec import UserSpec


class MedicationStatementStatus(str, Enum):
    active = "active"
    on_hold = "on_hold"
    completed = "completed"
    stopped = "stopped"
    unknown = "unknown"
    entered_in_error = "entered_in_error"
    not_taken = "not_taken"
    intended = "intended"


class MedicationStatementInformationSourceType(str, Enum):
    related_person = "related_person"
    practitioner = "practitioner"
    patient = "patient"


class BaseMedicationStatementSpec(EMRResource):
    __model__ = MedicationStatement
    __exclude__ = ["patient", "encounter"]
    id: UUID4 = None

    status: MedicationStatementStatus
    reason: str | None = None

    medication: Coding = Field(
        json_schema_extra={"slug": CARE_MEDICATION_VALUESET.slug},
    )
    dosage_text: str | None = Field(
        None,
    )  # consider using Dosage from MedicationRequest

    effective_period: Period | None = None

    encounter: UUID4

    information_source: MedicationStatementInformationSourceType | None = None

    note: str | None = None


class MedicationStatementSpec(BaseMedicationStatementSpec):
    @field_validator("encounter")
    @classmethod
    def validate_encounter_exists(cls, encounter):
        if not Encounter.objects.filter(external_id=encounter).exists():
            err = "Encounter not found"
            raise ValueError(err)
        return encounter

    @field_validator("medication")
    @classmethod
    def validate_medication(cls, medication):
        return validate_valueset(
            "medication",
            cls.model_fields["medication"].json_schema_extra["slug"],
            medication,
        )

    def perform_extra_deserialization(self, is_update, obj):
        if not is_update:
            obj.encounter = Encounter.objects.get(
                external_id=self.encounter
            )  # Needs more validation
            obj.patient = obj.encounter.patient


class MedicationStatementReadSpec(BaseMedicationStatementSpec):
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
