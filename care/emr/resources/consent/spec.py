from datetime import datetime
from enum import Enum

from pydantic import UUID4, BaseModel, Field

from care.emr.models import Encounter, FileUpload
from care.emr.models.consent import Consent
from care.emr.resources.base import EMRResource, PeriodSpec
from care.emr.resources.file_upload.spec import (
    FileUploadListSpec,
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
    verified_by: UUID4 | None = None
    verification_date: datetime | None = None
    verification_type: VerificationType


class ConsentBaseSpec(EMRResource):
    __model__ = Consent

    id: UUID4 | None = Field(
        default=None, description="Unique identifier for the consent record"
    )
    status: ConsentStatusChoices
    category: CategoryChoice
    date: datetime
    period: PeriodSpec = dict
    encounter: UUID4
    decision: DecisionType


class ConsentCreateSpec(ConsentBaseSpec):
    def perform_extra_deserialization(self, is_update, obj):
        if not is_update:
            obj.encounter = Encounter.objects.get(external_id=self.encounter)


class ConsentUpdateSpec(ConsentBaseSpec):
    status: ConsentStatusChoices | None = None
    category: CategoryChoice | None = None
    date: datetime | None = None
    period: PeriodSpec | None = None
    encounter: UUID4 | None = None
    decision: DecisionType | None = None

    def perform_extra_deserialization(self, is_update, obj):
        if is_update:
            self.encounter = obj.encounter


class ConsentListSpec(ConsentBaseSpec):
    source_attachments: list[dict] = []
    verification_details: list[dict] = []

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["source_attachments"] = [
            FileUploadListSpec.serialize(attachment).to_json()
            for attachment in FileUpload.objects.filter(associating_id=obj.external_id)
        ]
        mapping["encounter"] = obj.encounter.external_id
        mapping["verification_details"] = obj.verification_details


class ConsentRetrieveSpec(ConsentListSpec):
    pass
