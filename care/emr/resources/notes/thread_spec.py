import datetime

from pydantic import UUID4, field_validator

from care.emr.models import Encounter
from care.emr.models.notes import NoteThread
from care.emr.resources.base import EMRResource
from care.emr.resources.user.spec import UserSpec


class NoteThreadSpec(EMRResource):
    __model__ = NoteThread
    __exclude__ = ["patient", "encounter"]
    id: UUID4 | None = None
    title: str


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
    created_by: UserSpec = dict
    updated_by: UserSpec = dict
    created_date: datetime.datetime
    modified_date: datetime.datetime

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id

        if obj.created_by:
            mapping["created_by"] = UserSpec.serialize(obj.created_by).to_json()
        if obj.updated_by:
            mapping["updated_by"] = UserSpec.serialize(obj.updated_by).to_json()
