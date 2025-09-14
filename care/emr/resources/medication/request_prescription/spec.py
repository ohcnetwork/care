from datetime import datetime
from enum import Enum

from pydantic import UUID4

from care.emr.models.encounter import Encounter
from care.emr.models.medication_request import MedicationRequestPrescription
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


class SimpleMedicationRequestSpec:
    """Simple spec to avoid circular imports when including medication requests in prescription response"""
    
    @classmethod
    def serialize(cls, obj):
        return {
            "id": obj.external_id,
            "status": obj.status,
            "intent": obj.intent,
            "category": obj.category,
            "priority": obj.priority,
            "medication": obj.medication,
            "dosage_instruction": obj.dosage_instruction,
            "note": obj.note,
            "authored_on": obj.authored_on,
            "dispense_status": obj.dispense_status,
            "created_date": obj.created_date,
            "modified_date": obj.modified_date,
        }


class SimpleMedicationRequestPrescriptionSpec:
    """Simple spec to avoid circular references when including prescription in medication request response"""
    
    @classmethod
    def serialize(cls, obj):
        from care.emr.tagging.base import SingleFacilityTagManager
        from care.emr.resources.base import model_from_cache
        
        data = {
            "id": obj.external_id,
            "status": obj.status,
            "note": obj.note,
            "name": obj.name,
            "created_date": obj.created_date,
            "modified_date": obj.modified_date,
            "tags": SingleFacilityTagManager().render_tags(obj),
        }
        
        if obj.prescribed_by:
            data["prescribed_by"] = model_from_cache(
                UserSpec, id=obj.prescribed_by_id
            )
        
        return data


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
    medication_requests: list[dict] = []

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        if obj.prescribed_by:
            mapping["prescribed_by"] = model_from_cache(
                UserSpec, id=obj.prescribed_by_id
            )
        mapping["tags"] = SingleFacilityTagManager().render_tags(obj)
        # Include related medication requests
        medication_requests = []
        for med_request in obj.medication_requests.all():
            medication_requests.append(SimpleMedicationRequestSpec.serialize(med_request))
        mapping["medication_requests"] = medication_requests


class MedicationRequestPrescriptionRetrieveSpec(MedicationRequestPrescriptionReadSpec):
    created_by: UserSpec = {}
    updated_by: UserSpec = {}

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        cls.serialize_audit_users(mapping, obj)


class MedicationRequestPrescriptionRetrieveDetailedSpec(
    MedicationRequestPrescriptionRetrieveSpec
):
    encounter: dict = {}

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        mapping["encounter"] = EncounterListSpec.serialize(obj.encounter).to_json()
