import datetime
from enum import Enum

from django.conf import settings
from django.core.exceptions import ValidationError
from pydantic import UUID4, field_validator

from care.emr.models import FileUpload
from care.emr.resources.base import EMRResource
from care.emr.resources.user.spec import UserSpec
from care.utils.models.validators import file_name_validator


class FileTypeChoices(str, Enum):
    patient = "patient"
    encounter = "encounter"
    consent = "consent"


class FileCategoryChoices(str, Enum):
    audio = "audio"
    xray = "xray"
    identity_proof = "identity_proof"
    unspecified = "unspecified"
    discharge_summary = "discharge_summary"
    consent_attachment = "consent_attachment"


class FileUploadBaseSpec(EMRResource):
    __model__ = FileUpload

    id: UUID4 | None = None
    name: str


class FileUploadUpdateSpec(FileUploadBaseSpec):
    pass


class FileUploadCreateSpec(FileUploadBaseSpec):
    original_name: str
    file_type: FileTypeChoices
    file_category: FileCategoryChoices
    associating_id: str
    mime_type: str

    def perform_extra_deserialization(self, is_update, obj):
        # Authz Performed in the request
        obj._just_created = True  # noqa SLF001
        obj.internal_name = self.original_name
        obj.meta["mime_type"] = self.mime_type

    @field_validator("mime_type")
    @classmethod
    def validate_mime_type(cls, mime_type: str):
        if mime_type not in settings.ALLOWED_MIME_TYPES:
            err = "Invalid mime type"
            raise ValueError(err)
        return mime_type

    @field_validator("original_name")
    @classmethod
    def validate_original_name(cls, original_name: str):
        if not original_name:
            err = "File name cannot be empty"
            raise ValueError(err)
        try:
            file_name_validator(original_name)
        except ValidationError as e:
            raise ValueError(e.message) from e
        return original_name


class FileUploadListSpec(FileUploadBaseSpec):
    file_type: FileTypeChoices
    file_category: FileCategoryChoices
    associating_id: str
    archived_by: UserSpec | None = None
    archived_datetime: datetime.datetime | None = None
    upload_completed: bool
    is_archived: bool | None = None
    archive_reason: str | None = None
    created_date: datetime.datetime
    extension: str
    uploaded_by: dict
    mime_type: str

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["extension"] = obj.get_extension()
        mapping["mime_type"] = obj.meta.get("mime_type")
        if obj.created_by:
            mapping["uploaded_by"] = UserSpec.serialize(obj.created_by)


class FileUploadRetrieveSpec(FileUploadListSpec):
    signed_url: str | None = None
    read_signed_url: str | None = None
    internal_name: str  # Not sure if this needs to be returned

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        if getattr(obj, "_just_created", False):
            # Calculate Write URL and return it
            mapping["signed_url"] = obj.files_manager.signed_url(obj)
        else:
            mapping["read_signed_url"] = obj.files_manager.read_signed_url(obj)

        if obj.updated_by:
            mapping["updated_by"] = UserSpec.serialize(obj.updated_by)


class ConsentFileUploadCreateSpec(FileUploadBaseSpec):
    original_name: str
    associating_id: UUID4

    def perform_extra_deserialization(self, is_update, obj):
        # Authz Performed in the request
        obj._just_created = True  # noqa SLF001
        obj.internal_name = self.original_name
        obj.file_type = FileTypeChoices.consent
        obj.file_category = FileCategoryChoices.consent_attachment
