from enum import Enum

from pydantic import UUID4, field_validator, model_validator

from care.emr.models.report.template import Template
from care.emr.reports.renderer.template_engine import TemplateEngine
from care.emr.reports.report_type_registry import ReportTypeRegistry
from care.emr.reports.template_validator import (
    validate_context_config_completeness,
    validate_template_fields,
)
from care.emr.resources.base import EMRResource
from care.emr.resources.facility.spec import FacilityBareMinimumSpec
from care.emr.resources.report.context_config.spec import ContextConfigSpec
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
    context_config: dict = {}
    template_data: str

    def perform_extra_deserialization(self, is_update, obj):
        if self.facility:
            obj.facility = Facility.objects.get(external_id=self.facility)
        obj.slug = self.slug_value

    @field_validator("template_data")
    @classmethod
    def validate_template_syntax(cls, v):
        template_engine = TemplateEngine()

        valid, error = template_engine.validate_syntax(v)
        if not valid:
            msg = f"Template syntax validation failed: {error}"
            raise ValueError(msg)

        valid, error = validate_template_fields(v)
        if not valid:
            raise ValueError(error)

        return v

    @field_validator("context_config")
    @classmethod
    def validate_context_config(cls, v):
        if not v:
            return v

        try:
            ContextConfigSpec.model_validate(v)
        except ValueError as e:
            raise ValueError(str(e)) from e
        except Exception as e:
            raise ValueError("Invalid context_config") from e

        return v

    @model_validator(mode="after")
    def validate_template_and_context_config(self):
        valid, error = validate_context_config_completeness(
            self.template_data, self.context_config
        )
        if not valid:
            raise ValueError(error)

        return self


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
    context_config: dict = {}

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        if obj.facility:
            mapping["facility"] = FacilityBareMinimumSpec.serialize(
                obj.facility
            ).to_json()
