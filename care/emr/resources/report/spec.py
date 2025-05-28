import datetime
from enum import Enum

from pydantic import UUID4

from care.emr.models import Report
from care.emr.resources.base import EMRResource
from care.emr.resources.user.spec import UserSpec


class ReportTypeChoices(str, Enum):
    discharge_summary = "discharge_summary"
    lab_report = "lab_report"


class ReportBaseSpec(EMRResource):
    __model__ = Report

    id: UUID4 | None = None
    name: str


class ReportListSpec(ReportBaseSpec):
    file_type: ReportTypeChoices
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


class ReportRetrieveSpec(ReportListSpec):
    signed_url: str | None = None
    read_signed_url: str | None = None
    internal_name: str  # Not sure if this needs to be returned

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        if getattr(obj, "_just_created", False):
            # Calculate Write URL and return it
            mapping["signed_url"] = obj.reports_manager.signed_url(obj)
        else:
            mapping["read_signed_url"] = obj.reports_manager.read_signed_url(obj)

        if obj.updated_by:
            mapping["updated_by"] = UserSpec.serialize(obj.updated_by)
