from datetime import datetime
from enum import Enum

from pydantic import UUID4, BaseModel, Field

from care.emr.models import Encounter, FileUpload
from care.emr.models.consent import Consent
from care.emr.resources.base import EMRResource, PeriodSpec
from care.emr.resources.file_upload.spec import (
    FileUploadListSpec,
    FileUploadRetrieveSpec,
)


class ConsentStatusChoices(str, Enum):
    draft = "draft"
    active = "active"
    inactive = "inactive"
    not_done = "not_done"
    entered_in_error = "entered_in_error"
    unknown = "unknown"


class VerificationType(str, Enum):
    family = "family"
    validation = "validation"


class DecisionType(str, Enum):
    deny = "deny"
    permit = "permit"


class CategoryChoice(str, Enum):
    research = "research"
    privacy_consent = "privacy_consent"
    treatment = "treatment"


class ConsentVerificationSpec(BaseModel):
    verified: bool
    verified_by: UUID4 | None
    verification_date: datetime | None
    verification_type: VerificationType


class ConsentBaseSpec(EMRResource):
    __model__ = Consent
    __exclude__ = ["encounter"]

    id: UUID4 | None = Field(
        default=None, description="Unique identifier for the consent record"
    )
    status: ConsentStatusChoices
    category: CategoryChoice
    date: datetime
    period: PeriodSpec = dict
    encounter: UUID4
    decision: DecisionType
    verification_details: list[ConsentVerificationSpec] | None = []


class ConsentCreateSpec(ConsentBaseSpec):
    def perform_extra_deserialization(self, is_update, obj):
        obj.encounter = Encounter.objects.get(external_id=self.encounter)


class ConsentUpdateSpec(ConsentBaseSpec):
    def perform_extra_deserialization(self, is_update, obj):
        self.verification_details = obj.verification_details  # Not updating this field
        self.encounter = obj.encounter  # Not updating this field


class ConsentListSpec(ConsentBaseSpec):
    source_attachment: list[dict] = []

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["source_attachment"] = [
            FileUploadListSpec.serialize(
                FileUpload.objects.get(external_id=attachment)
            ).to_json()
            for attachment in obj.source_attachment or []
        ]
        mapping["encounter"] = obj.encounter.external_id
        mapping["source_attachment"] = [
            FileUploadRetrieveSpec.serialize(
                FileUpload.objects.get(external_id=attachment)
            ).to_json()
            for attachment in obj.source_attachment or []
        ]


class ConsentRetrieveSpec(ConsentBaseSpec):
    source_attachment: list[dict] = []

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id

        mapping["source_attachment"] = [
            FileUploadRetrieveSpec.serialize(
                FileUpload.objects.get(external_id=attachment)
            ).to_json()
            for attachment in obj.source_attachment or []
        ]
        mapping["encounter"] = obj.encounter.external_id
