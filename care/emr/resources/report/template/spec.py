from enum import Enum

from pydantic import UUID4, field_validator

from care.emr.models.report.template import Template
from care.emr.reports.context_builder.data_point_registry import DataPointRegistry
from care.emr.reports.report_type_registry import ReportTypeRegistry
from care.emr.resources.base import EMRResource
from care.emr.resources.facility.spec import FacilityBareMinimumSpec
from care.emr.utils.slug_type import SlugType
from care.facility.models.facility import Facility


class TemplateStatusOptions(str, Enum):
    draft = "draft"
    active = "active"
    retired = "retired"


class TemplateFormatOptions(str, Enum):
    pdf = "pdf"
    html = "html"


class TemplateBaseSpec(EMRResource):
    __model__ = Template

    __exclude__ = ["facility"]

    id: UUID4 | None = None
    name: str
    status: TemplateStatusOptions
    template_type: str
    default_format: TemplateFormatOptions
    description: str = ""

    @field_validator("template_type")
    @classmethod
    def validate_template_type(cls, v):
        valid_types = ReportTypeRegistry.get_all_keys()
        if v not in valid_types:
            msg = f"Invalid template_type '{v}'. Valid types are: {', '.join(valid_types)}"
            raise ValueError(msg)
        return v


class TemplateCreateSpec(TemplateBaseSpec):
    facility: UUID4 | None = None
    slug_value: SlugType
    context: str
    template_data: str

    def perform_extra_deserialization(self, is_update, obj):
        if self.facility:
            obj.facility = Facility.objects.get(external_id=self.facility)
        obj.slug = self.slug_value

    @field_validator("context")
    @classmethod
    def validate_context(cls, v):
        if not v:
            msg = "context is required"
            raise ValueError(msg)

        available_contexts = list(DataPointRegistry.get_all().keys())
        if v not in available_contexts:
            msg = f"Invalid context '{v}'. Available contexts: {', '.join(available_contexts)}"
            raise ValueError(msg)

        return v


class TemplateUpdateSpec(TemplateCreateSpec):
    pass


class TemplateReadSpec(TemplateBaseSpec):
    slug_config: dict
    slug: str

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["slug_config"] = obj.parse_slug(obj.slug)


class TemplateRetrieveSpec(TemplateReadSpec):
    facility: dict | None = None
    template_data: str
    context: str

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        if obj.facility:
            mapping["facility"] = FacilityBareMinimumSpec.serialize(
                obj.facility
            ).to_json()
