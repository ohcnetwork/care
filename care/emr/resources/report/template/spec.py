from enum import Enum

from pydantic import UUID4, field_validator, model_validator

from care.emr.models.report.template import Template
from care.emr.reports.context_builder.data_point_registry import DataPointRegistry
from care.emr.reports.renderer.generators import GeneratorRegistry
from care.emr.reports.report_type_registry import ReportTypeRegistry
from care.emr.resources.base import EMRResource
from care.emr.resources.facility.spec import FacilityBareMinimumSpec
from care.emr.utils.slug_type import SlugType
from care.facility.models.facility import Facility
from care.utils.shortcuts import get_object_or_404


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
    default_format: TemplateFormatOptions
    description: str = ""
    options: dict = {}


class TemplateCreateSpec(TemplateBaseSpec):
    facility: UUID4 | None = None
    slug_value: SlugType
    template_data: str
    template_type: str
    context: str

    def perform_extra_deserialization(self, is_update, obj):
        if self.facility:
            obj.facility = get_object_or_404(Facility, external_id=self.facility)
        obj.slug = self.slug_value

    @model_validator(mode="after")
    def validate_report_type_and_context(self):
        template_type = ReportTypeRegistry.get(self.template_type)
        context = DataPointRegistry.get(self.context)
        if not template_type or not context:
            raise ValueError("Invalid report type or context")
        if template_type.associating_model != context.__associating_model__:
            raise ValueError("Report Type and Context are not compatible")

        generator_class = GeneratorRegistry.get(self.default_format)

        options_model = generator_class.options_model
        options_model.model_validate(self.options)

        return self

    @field_validator("template_type")
    @classmethod
    def validate_report_type(cls, v):
        if not v:
            msg = "Report Type is required"
            raise ValueError(msg)
        try:
            ReportTypeRegistry.get(v)
        except KeyError as e:
            raise ValueError("Invalid report type") from e
        return v

    @field_validator("context")
    @classmethod
    def validate_context(cls, v):
        if not v:
            msg = "Report Type is required"
            raise ValueError(msg)
        try:
            DataPointRegistry.get(v)
        except KeyError as e:
            raise ValueError("Invalid Context type") from e
        return v


class TemplateUpdateSpec(TemplateCreateSpec):
    pass


class TemplateReadSpec(TemplateBaseSpec):
    slug_config: dict
    slug: str
    template_type: str
    context: str

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["slug_config"] = obj.parse_slug(obj.slug)


class TemplateRetrieveSpec(TemplateReadSpec):
    facility: dict | None = None
    template_data: str

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        if obj.facility:
            mapping["facility"] = FacilityBareMinimumSpec.serialize(
                obj.facility
            ).to_json()
