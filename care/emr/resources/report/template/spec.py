from enum import Enum

from pydantic import UUID4, field_validator

from care.emr.models.report.template import Template
from care.emr.reports.context_builder.report_builder import ReportContextBuilder
from care.emr.reports.renderer.template_engine import TemplateEngine
from care.emr.reports.report_type_registry import ReportTypeRegistry
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

        cls._validate_template_fields(v, template_engine)

        return v

    @classmethod
    def _validate_template_fields(
        cls, template_data: str, template_engine: TemplateEngine
    ):
        variables = template_engine.extract_variables(template_data)

        if not variables:
            return

        builder = ReportContextBuilder()
        schema = builder.get_full_schema()

        available_fields = {}

        for builder_key, builder_schema in schema["single_objects"].items():
            available_fields[builder_key] = {
                field["key"] for field in builder_schema["fields"]
            }

        for builder_key, builder_schema in schema["querysets"].items():
            available_fields[builder_key] = {
                field["key"] for field in builder_schema["fields"]
            }

        invalid_refs = []
        for var in variables:
            if var in ["loop", "current_date", "current_datetime", "current_time"]:
                continue

            parts = var.split(".")
            if len(parts) < 2:  # noqa: PLR2004
                continue

            builder_key = parts[0]

            if builder_key not in available_fields:
                continue

            # Checks for key.0.field as well
            field_key = (
                parts[1]
                if len(parts) >= 2 and not parts[1].isdigit()  # noqa: PLR2004
                else (parts[2] if len(parts) >= 3 else None)  # noqa: PLR2004
            )

            if field_key and field_key not in available_fields[builder_key]:
                available = ", ".join(sorted(available_fields[builder_key]))
                invalid_refs.append(
                    f"{var} (field '{field_key}' not found in '{builder_key}'. "
                    f"Available fields: {available})"
                )

        if invalid_refs:
            msg = "Invalid field references in template:\n  - " + "\n  - ".join(
                invalid_refs
            )
            raise ValueError(msg)

    @field_validator("context_config")
    @classmethod
    def validate_context_config(cls, v):
        if not v:
            return v

        try:
            ContextConfigSpec.model_validate(v)
        except Exception as e:
            msg = f"Invalid context_config: {e!s}"
            raise ValueError(msg) from e

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
    context_config: dict = {}

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        if obj.facility:
            mapping["facility"] = FacilityBareMinimumSpec.serialize(
                obj.facility
            ).to_json()
