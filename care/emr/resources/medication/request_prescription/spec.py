from datetime import datetime
from enum import Enum

from pydantic import UUID4

from care.emr.models.encounter import Encounter
from care.emr.models.medication_request import (
    MedicationRequest,
    MedicationRequestPrescription,
)
from care.emr.resources.base import EMRResource, model_from_cache
from care.emr.resources.encounter.spec import EncounterListSpec
from care.emr.resources.user.spec import UserSpec
from care.emr.tagging.base import SingleFacilityTagManager
from care.users.models import User


class MedicationRequestPrescriptionStatus(str, Enum):
    active = "active"
    on_hold = "on_hold"
    ended = "ended"
    stopped = "stopped"
    completed = "completed"
    cancelled = "cancelled"
    entered_in_error = "entered_in_error"
    draft = "draft"


MEDICATION_PRESCRIPTION_PHARMACIST_ALLOWED_STATUS = [
    MedicationRequestPrescriptionStatus.active.value,
    MedicationRequestPrescriptionStatus.on_hold.value,
    MedicationRequestPrescriptionStatus.completed.value,
]


class MedicationRequestPrescriptionResource(EMRResource):
    __model__ = MedicationRequestPrescription
    __exclude__ = ["patient", "encounter"]


class BaseMedicationRequestPrescriptionSpec(MedicationRequestPrescriptionResource):
    id: UUID4 = None
    status: MedicationRequestPrescriptionStatus
    note: str | None = None
    name: str | None = None


class MedicationRequestPrescriptionWriteSpec(BaseMedicationRequestPrescriptionSpec):
    encounter: UUID4
    prescribed_by: UUID4

    def perform_extra_deserialization(self, is_update, obj):
        obj.encounter = Encounter.objects.get(external_id=self.encounter)
        obj.patient = obj.encounter.patient
        obj.prescribed_by = User.objects.get(external_id=self.prescribed_by)


class MedicationRequestPrescriptionUpdateSpec(BaseMedicationRequestPrescriptionSpec):
    pass


class MedicationRequestPrescriptionReadSpec(BaseMedicationRequestPrescriptionSpec):
    created_date: datetime
    modified_date: datetime
    prescribed_by: UserSpec = {}
    tags: list[dict] = []

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        if obj.prescribed_by:
            mapping["prescribed_by"] = model_from_cache(
                UserSpec, id=obj.prescribed_by_id
            )
        mapping["tags"] = SingleFacilityTagManager().render_tags(obj)


class MedicationRequestPrescriptionRetrieveSpec(MedicationRequestPrescriptionReadSpec):
    created_by: UserSpec = {}
    updated_by: UserSpec = {}

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        cls.serialize_audit_users(mapping, obj)


class MedicationRequestPrescriptionRetrieveMedicationsSpec(
    MedicationRequestPrescriptionRetrieveSpec
):
    medications: list[dict] = []

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        from care.emr.resources.medication.request.spec import (
            MedicationRequestReadWithoutPrescriptionSpec,
        )

        super().perform_extra_serialization(mapping, obj)
        cls.serialize_audit_users(mapping, obj)
        medications = MedicationRequest.objects.filter(prescription=obj).select_related(
            "requested_product"
        )
        mapping["medications"] = [
            MedicationRequestReadWithoutPrescriptionSpec.serialize(medication).to_json()
            for medication in medications
        ]


class MedicationRequestPrescriptionRetrieveDetailedSpec(
    MedicationRequestPrescriptionRetrieveSpec
):
    encounter: dict = {}

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        mapping["encounter"] = EncounterListSpec.serialize(obj.encounter).to_json()
