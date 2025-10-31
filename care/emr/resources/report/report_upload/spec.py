import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from pydantic import UUID4, field_validator, model_validator

from care.emr.models.report.report_upload import ReportUpload
from care.emr.models.report.template import Template
from care.emr.reports import report_types  # noqa: F401 - Trigger registration
from care.emr.reports.report_type_registry import ReportTypeRegistry
from care.emr.reports.report_type_utils import validate_associating_id
from care.emr.resources.base import EMRResource
from care.emr.resources.report.template.spec import TemplateReadSpec
from care.emr.resources.user.spec import UserSpec
from care.utils.models.validators import file_name_validator


class ReportUploadBaseSpec(EMRResource):
    __model__ = ReportUpload

    id: UUID4 | None = None
    name: str


class ReportUploadUpdateSpec(ReportUploadBaseSpec):
    pass


class ReportUploadCreateSpec(ReportUploadBaseSpec):
    template: str  # Template slug
    original_name: str
    report_type: str
    associating_id: str
    mime_type: str

    def perform_extra_deserialization(self, is_update, obj):
        # Authz Performed in the request
        obj._just_created = True  # noqa SLF001
        obj.internal_name = self.original_name
        obj.meta["mime_type"] = self.mime_type
        obj.template = Template.objects.get(slug=self.template)
        obj.report_type = self.report_type

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

    @field_validator("report_type")
    @classmethod
    def validate_report_type(cls, v):
        valid_types = ReportTypeRegistry.get_all_keys()
        if v not in valid_types:
            msg = f"Invalid report_type '{v}'. Valid types: {', '.join(valid_types)}"
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def validate_report_type_and_associating_id(self):
        try:
            config = ReportTypeRegistry.get(self.report_type)
            validate_associating_id(
                associating_model=config.associating_model,
                associating_id=self.associating_id,
                report_type_key=self.report_type,
                validator_func=config.validator,
            )
        except (KeyError, ValueError) as e:
            raise ValueError(str(e)) from e

        return self


class ReportUploadListSpec(ReportUploadBaseSpec):
    template: dict
    report_type: str
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
        if obj.template:
            mapping["template"] = TemplateReadSpec.serialize(obj.template).to_json()
        if obj.created_by:
            mapping["uploaded_by"] = UserSpec.serialize(obj.created_by)
        if obj.archived_by:
            mapping["archived_by"] = UserSpec.serialize(obj.archived_by)


class ReportUploadRetrieveSpec(ReportUploadListSpec):
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
