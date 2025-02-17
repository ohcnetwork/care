from datetime import datetime
from enum import Enum

from pydantic import UUID4, Field

from care.emr.fhir.schema.base import Coding, Period
from care.emr.models.consent import Consent
from care.emr.resources.base import EMRResource
from care.emr.resources.file_upload.spec import FileUploadBaseSpec


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


class ConsentVerificationSpec(EMRResource):
    verified: bool
    verified_by: UUID4
    verification_date: datetime
    verification_type: VerificationType


class DecisionType(str, Enum):
    deny = "deny"
    permit = "permit"


class ConsentSpec(EMRResource):
    __model__ = Consent
    id: UUID4 | None = Field(
        default=None, description="Unique identifier for the consent record"
    )
    status: ConsentStatusChoices
    category: list[Coding]
    date: datetime
    period: Period | None = None
    encounter: UUID4
    decision: DecisionType
    source_attachment: list[FileUploadBaseSpec] | None = None
    verification_details: list[ConsentVerificationSpec] | None = None
