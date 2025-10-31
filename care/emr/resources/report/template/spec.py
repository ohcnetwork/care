from enum import Enum

from pydantic import UUID4, field_validator

from care.emr.models.report.template import Template
from care.emr.reports.renderer.template_engine import TemplateEngine
from care.emr.resources.base import EMRResource
from care.emr.resources.facility.spec import FacilityBareMinimumSpec
from care.emr.resources.report.context_config.spec import ContextConfigSpec
from care.emr.utils.slug_type import SlugType
from care.facility.models.facility import Facility


class TemplateStatusOptions(str, Enum):
    draft = "draft"
    active = "active"
    retired = "retired"


class TemplateTypeOptions(str, Enum):
    discharge_summary = "discharge_summary"


class TemplateFormatOptions(str, Enum):
    pdf = "pdf"
    html = "html"


class TemplateBaseSpec(EMRResource):
    __model__ = Template

    __exclude__ = ["facility"]

    id: UUID4 | None = None
    name: str
    status: TemplateStatusOptions
    template_data: str
    template_type: TemplateTypeOptions
    format: TemplateFormatOptions
    context_config: dict = {}

    @field_validator("template_data")
    @classmethod
    def validate_template_syntax(cls, v):
        """Validate Jinja2 template syntax before saving"""
        template_engine = TemplateEngine()
        valid, error = template_engine.validate_syntax(v)
        if not valid:
            msg = f"Template syntax validation failed: {error}"
            raise ValueError(msg)
        return v

    @field_validator("context_config")
    @classmethod
    def validate_context_config(cls, v):
        """Validate context_config structure and field names"""
        if not v:
            return v

        try:
            ContextConfigSpec.model_validate(v)
        except Exception as e:
            msg = f"Invalid context_config: {e!s}"
            raise ValueError(msg) from e

        return v


class TemplateCreateSpec(TemplateBaseSpec):
    facility: UUID4 | None = None
    slug_value: SlugType

    def perform_extra_deserialization(self, is_update, obj):
        if self.facility:
            obj.facility = Facility.objects.get(external_id=self.facility)
        obj.slug = self.slug_value


class TemplateUpdateSpec(TemplateBaseSpec):
    slug_value: SlugType

    def perform_extra_deserialization(self, is_update, obj):
        obj.slug = self.slug_value


class TemplateReadSpec(TemplateBaseSpec):
    slug_config: dict
    slug: str

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["slug_config"] = obj.parse_slug(obj.slug)


class TemplateRetrieveSpec(TemplateReadSpec):
    facility: dict | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        if obj.facility:
            mapping["facility"] = FacilityBareMinimumSpec.serialize(
                obj.facility
            ).to_json()
