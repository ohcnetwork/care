from datetime import datetime
from enum import Enum

from pydantic import UUID4, Field

from care.emr.models import FileUpload
from care.emr.models.consent import Consent
from care.emr.resources.base import EMRResource, PeriodSpec
from care.emr.resources.file_upload.spec import (
    FileCategoryChoices,
    FileTypeChoices,
    FileUploadCreateSpec,
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


class ConsentVerificationSpec(EMRResource):
    verified: bool
    verified_by: UUID4
    verification_date: datetime
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
    verification_details: list[ConsentVerificationSpec] | None = []


class ConsentCreateSpec(ConsentBaseSpec):
    source_attachment: list[FileUploadCreateSpec] | None = []

    def perform_extra_deserialization(self, is_update, obj):
        if not is_update:
            for attachment in self.source_attachment:
                attachment.file_type = FileTypeChoices.consent
                attachment.file_category = FileCategoryChoices.consent_attachment
            # obj.source_attachment = [attachment.id for attachment in self.source_attachment]


class ConsentUpdateSpec(ConsentBaseSpec):
    pass


class ConsentListSpec(ConsentBaseSpec):
    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["source_attachment"] = [
            FileUploadListSpec.serialize(
                FileUpload.objects.get(external_id=attachment)
            ).to_json()
            for attachment in obj.source_attachment or []
        ]


class ConsentRetrieveSpec(ConsentBaseSpec):
    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["source_attachment"] = [
            FileUploadRetrieveSpec.serialize(
                FileUpload.objects.get(external_id=attachment)
            ).to_json()
            for attachment in obj.source_attachment or []
        ]
