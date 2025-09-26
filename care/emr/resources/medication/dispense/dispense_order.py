from enum import Enum

from pydantic import UUID4

from care.emr.models.location import FacilityLocation
from care.emr.models.medication_dispense import DispenseOrder
from care.emr.models.patient import Patient
from care.emr.resources.base import EMRResource
from care.emr.resources.location.spec import FacilityLocationListSpec
from care.emr.resources.patient.spec import PatientListSpec
from care.utils.shortcuts import get_object_or_404


class MedicationDispenseOrderStatusOptions(str, Enum):
    draft = "draft"
    in_progress = "in_progress"
    completed = "completed"
    abandoned = "abandoned"
    entered_in_error = "entered_in_error"


MEDICATION_DISPENSE_ORDER_COMPLETED_STATUSES = [
    MedicationDispenseOrderStatusOptions.abandoned.value,
    MedicationDispenseOrderStatusOptions.entered_in_error.value,
    MedicationDispenseOrderStatusOptions.completed.value,
]


class BaseMedicationDispenseOrderSpec(EMRResource):
    __model__ = DispenseOrder

    id: UUID4 | None = None

    status: MedicationDispenseOrderStatusOptions
    name: str
    note: str | None = None


class MedicationDispenseOrderWriteSpec(BaseMedicationDispenseOrderSpec):
    patient: UUID4
    location: UUID4

    def perform_extra_deserialization(self, is_update, obj):
        obj.patient = get_object_or_404(
            Patient.objects.only("id"), external_id=self.patient
        )
        obj.location = get_object_or_404(
            FacilityLocation.objects.only("id"), external_id=self.location
        )
        return obj


class MedicationDispenseOrderReadSpec(BaseMedicationDispenseOrderSpec):
    patient: dict
    location: dict

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["patient"] = PatientListSpec.serialize(obj.patient).to_json()
        mapping["location"] = FacilityLocationListSpec.serialize(obj.location).to_json()
