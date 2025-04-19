from enum import Enum

from pydantic import UUID4
from rest_framework.generics import get_object_or_404

from care.emr.resources.base import EMRResource
from care.emr.resources.facility.spec import FacilityRetrieveSpec
from care.emr.resources.user.spec import UserSpec
from care.facility.models import Facility, FacilityReportTemplate


class FacilityReportTemplateType(str, Enum):
    discharge_summary = "discharge_summary"
    lab_report = "lab_report"


class FacilityReportTemplateBaseSpec(EMRResource):
    id: UUID4 | None = None

    __model__ = FacilityReportTemplate


class FacilityReportTemplateCreateSpec(FacilityReportTemplateBaseSpec):
    config: dict = {}
    facility: UUID4
    type: FacilityReportTemplateType

    def perform_extra_deserialization(self, is_update, obj):
        obj.facility = get_object_or_404(Facility, external_id=self.facility)


class FacilityReportTemplateUpdateSpec(FacilityReportTemplateBaseSpec):
    config: dict = {}


class FacilityReportTemplateReadSpec(FacilityReportTemplateBaseSpec):
    config: dict
    facility: dict
    type: str

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["facility"] = FacilityRetrieveSpec.serialize(obj.facility)


class FacilityReportTemplateRetrieveSpec(FacilityReportTemplateReadSpec):
    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        if obj.created_by:
            mapping["created_by"] = UserSpec.serialize(obj.created_by).to_json()
        if obj.updated_by:
            mapping["updated_by"] = UserSpec.serialize(obj.updated_by).to_json()
