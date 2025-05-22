from datetime import datetime
from enum import Enum

from django.contrib.auth import get_user_model
from pydantic import UUID4, BaseModel, Field, model_validator
from rest_framework.exceptions import ValidationError

from care.emr.models import Encounter, FileUpload
from care.emr.models.consent import Consent
from care.emr.resources.base import EMRResource, PeriodSpec
from care.emr.resources.file_upload.spec import (
    FileCategoryChoices,
    FileTypeChoices,
    FileUploadListSpec,
)
from care.emr.resources.user.spec import UserSpec

User = get_user_model()


class ConsentStatusChoices(str, Enum):
    draft = "draft"
    active = "active"
    inactive = "inactive"
    not_done = "not_done"
    entered_in_error = "entered_in_error"


class VerificationType(str, Enum):
    family = "family"
    validation = "validation"


class DecisionType(str, Enum):
    deny = "deny"
    permit = "permit"


class CategoryChoice(str, Enum):
    research = "research"
    patient_privacy = "patient_privacy"
    treatment = "treatment"
    dnr = "dnr"
    comfort_care = "comfort_care"
    acd = "acd"
    adr = "adr"
    # consent_document = "consent_document"  # From LOINC 59284-0 # Only used in migrations


class ConsentVerificationSpec(BaseModel):
    verified: bool
    verified_by: UUID4 | None = None
    verification_date: datetime | None = None
    verification_type: VerificationType
    note: str | None = None


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
    note: str | None = None


class ConsentCreateSpec(ConsentBaseSpec):
    @model_validator(mode="after")
    def validate_period_and_date(self):
        if self.period.start and self.period.start < self.date:
            raise ValidationError(
                "Start of the period cannot be before than the Consent date"
            )
        return self

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
    note: str | None = None

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
            for attachment in FileUpload.objects.filter(
                associating_id=obj.external_id,
                file_category=FileCategoryChoices.consent_attachment,
                file_type=FileTypeChoices.consent,
            )
        ]
        mapping["encounter"] = obj.encounter.external_id

        for verification in obj.verification_details:
            verification["verified_by"] = UserSpec.serialize(
                User.objects.get(external_id=verification["verified_by"])
            ).to_json()

        mapping["verification_details"] = obj.verification_details


class ConsentRetrieveSpec(ConsentListSpec):
    pass
