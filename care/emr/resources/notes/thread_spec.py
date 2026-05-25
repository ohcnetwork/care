import datetime

from pydantic import UUID4, Field, field_validator

from care.emr.models import Encounter
from care.emr.models.notes import NoteThread
from care.emr.resources.base import EMRResource


class NoteThreadSpec(EMRResource):
    __model__ = NoteThread
    __exclude__ = ["patient", "encounter"]
    id: UUID4 | None = None
    title: str = Field(..., max_length=255)


class NoteThreadCreateSpec(NoteThreadSpec):
    encounter: UUID4 | None = None

    @field_validator("encounter")
    @classmethod
    def validate_encounter_exists(cls, encounter):
        if encounter and not Encounter.objects.filter(external_id=encounter).exists():
            err = "Encounter not found"
            raise ValueError(err)
        return encounter

    def perform_extra_deserialization(self, is_update, obj):
        if self.encounter:
            obj.encounter = Encounter.objects.get(external_id=self.encounter)


class NoteThreadUpdateSpec(NoteThreadSpec):
    pass


class NoteThreadReadSpec(NoteThreadSpec):
    created_by: dict | None = None
    updated_by: dict | None = None
    created_date: datetime.datetime
    modified_date: datetime.datetime

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        cls.serialize_audit_users(mapping, obj)
