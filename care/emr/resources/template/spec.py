import re
import tempfile
from enum import Enum
from pathlib import Path
from typing import Annotated, Literal

import magic
import requests
from django.conf import settings
from django.shortcuts import get_object_or_404
from pydantic import (
    UUID4,
    BaseModel,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

from care.emr.models.template import ReportTemplate
from care.emr.registries.report.section import SectionRegistry
from care.emr.reports.renderer.dummy import DummyRenderer
from care.emr.resources.base import EMRResource
from care.emr.resources.facility.spec import FacilityRetrieveSpec
from care.emr.resources.user.spec import UserSpec
from care.facility.models import Facility


class MarginValues(BaseModel):
    top: str
    bottom: str
    right: str
    left: str


class PageMargin(BaseModel):
    mode: Literal["uniform", "custom"]
    value: str | None = None
    values: MarginValues | None = None

    @model_validator(mode="after")
    def validate_margin(self):
        if self.mode == "uniform" and not self.value:
            raise ValueError("Value is required for uniform margin mode")
        if self.mode == "custom" and not self.values:
            raise ValueError("Values are required for custom margin mode")
        return self


class PageNumbering(BaseModel):
    enabled: bool
    format: str
    align: Literal[
        "left",
        "center",
        "right",
        "right + bottom",
        "left + bottom",
        "center + bottom",
        "top+left",
        "top+right",
        "top+center",
    ]


class TextConfig(BaseModel):
    font: str
    size: str


class Layout(BaseModel):
    page_size: str
    page_margin: PageMargin
    page_numbering: PageNumbering
    text: TextConfig


class StyleConfig(BaseModel):
    fill: str | None = 'rgb("#808080")'
    weight: int | None = None

    @field_validator("fill")
    @classmethod
    def validate_fill_format(cls, value):
        if value is None:
            return value

        pattern = r"^#[0-9a-fA-F]{6}$"
        if not re.match(pattern, value):
            raise ValueError('Fill must be in format: #RRGGBB" (color hex code)')
        return value


class TextElement(BaseModel):
    type: Literal["text"]
    text: str
    size: str
    weight: int
    align: Literal["left", "center", "right"] | None = None


class ImageElement(BaseModel):
    type: Literal["image"]
    file_name: str
    url: HttpUrl
    width: str | None = None
    align: Literal["left", "center", "right"] | None = None

    @model_validator(mode="after")
    def fix_filename_extension(self) -> "ImageElement":
        try:
            response = requests.get(self.url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            error = f"Failed to download image from {self.url}. Please Recheck the URL."
            raise ValueError(error) from e

        if len(response.content) > settings.MAX_IMAGE_SIZE_FOR_REPORTS * 1024 * 1024:
            error = f"Image from {self.url} exceeds maximum allowed size of {settings.MAX_IMAGE_SIZE_FOR_REPORTS}MB"
            raise ValueError(error)

        tmp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                tmp_file.write(response.content)
                tmp_path = Path(tmp_file.name)

            mime_type = magic.from_file(str(tmp_path), mime=True)
            extension_map = {
                "image/svg+xml": ".svg",
                "image/png": ".png",
                "image/jpeg": ".jpg",
                "image/gif": ".gif",
                "image/webp": ".webp",
            }
            ext = extension_map.get(mime_type)

            if not ext:
                error = f"Unsupported or unknown image format: {mime_type}"
                raise ValueError(error)

            file_path = Path(self.file_name)
            if file_path.suffix.lower() != ext:
                self.file_name = f"{file_path.stem}{ext}"

        finally:
            if tmp_path and tmp_path.exists():
                tmp_path.unlink()

        return self


class RuleElement(BaseModel):
    type: Literal["rule"]
    length: int = 100
    stroke: str | None = 'rgb("#808080")'
    align: Literal["left", "center", "right"] | None = "center"

    @field_validator("stroke")
    @classmethod
    def validate_stroke_format(cls, value):
        if value is None:
            return value

        pattern = r"^#[0-9a-fA-F]{6}$"
        if not re.match(pattern, value):
            raise ValueError('stroke must be in format: #RRGGBB" (color hex code)')
        return value

    @model_validator(mode="after")
    def validate_length_range(self) -> "RuleElement":
        if not (0 <= self.length <= 100):  # noqa PLR2004
            raise ValueError("length must be between 0 and 100")
        return self


class DateTimeElement(BaseModel):
    type: Literal["datetime"]
    label: str
    format: Literal[
        "[day]/[month]/[year]",
        "[month]/[day]/[year]",
        "[year]/[month]/[day]",
        "[day]-[month]-[year]",
        "[month]-[day]-[year]",
        "[year]-[month]-[day]",
        "[year]-[day]-[month]",
    ]
    style: StyleConfig
    align: Literal["left", "center", "right"] | None = None


class HeaderRow(BaseModel):
    size_ratio: list[int] = [1]
    columns: list[
        Annotated[
            TextElement | ImageElement | RuleElement | DateTimeElement,
            Field(discriminator="type"),
        ]
    ]

    @model_validator(mode="after")
    def validate_size_ratio_length(self):
        if len(self.size_ratio) != len(self.columns):
            error = f"Size ratio {self.size_ratio} does not match number of columns {len(self.columns)}"
            raise ValueError(error)
        return self


class HeaderConfig(BaseModel):
    rows: list[HeaderRow]


class LabelValueField(BaseModel):
    label: str
    value: str


class SectionOptions(BaseModel):
    title: str | None = None
    fields: list[str] | list[LabelValueField] = []
    columns: list[str] = []
    style: Literal["list", "text"] | None = None
    filters: dict[str, list[str]] | None = None
    text: str | None = None
    rows: list[list[str]] | None = []


class SectionConfig(BaseModel):
    source: str
    is_table: bool
    enabled: bool
    options: SectionOptions

    @model_validator(mode="after")
    def validate_section(self):
        if not self.is_table:
            if not (self.options.fields or self.options.text):
                raise ValueError(
                    "Non-table sections must have either 'fields' or 'text'"
                )
        elif not (self.options.columns or self.options.rows):
            raise ValueError("Table sections must have either 'columns' or 'rows'")

        if self.source == "custom_section":
            return self

        section_cls = SectionRegistry.get(self.source)
        if not section_cls:
            error = f"Section {self.source} does not exist"
            raise ValueError(error)

        section = section_cls(config={}, context={}, renderer=DummyRenderer())
        allowed_fields = section.available_fields()

        if not self.is_table:
            for field in self.options.fields:
                if field not in allowed_fields and not isinstance(
                    field, LabelValueField
                ):
                    error = f"Section {self.source} does not support field {field}"
                    raise ValueError(error)

        if self.is_table:
            for col in self.options.columns:
                if col not in allowed_fields:
                    error = f"Section {self.source} does not support column {col}"
                    raise ValueError(error)

        return self


class ReportConfig(BaseModel):
    layout: Layout
    header: HeaderConfig
    sections: list[SectionConfig]


class ReportTemplateTypes(str, Enum):
    discharge_summary = "discharge_summary"
    lab_report = "lab_report"


class ReportTemplateBaseSpec(EMRResource):
    id: UUID4 | None = None
    facility: UUID4 | None = None

    __model__ = ReportTemplate
    __exclude__ = ["facility"]


class ReportTemplateCreateSpec(ReportTemplateBaseSpec):
    config: ReportConfig
    slug: str
    type: ReportTemplateTypes
    derived_from_url: str | None = None

    @model_validator(mode="after")
    def validate_slug(self):
        if len(self.slug) < 5 or len(self.slug) > 25:  # noqa PLR2004
            error = "Slug must be between 5 and 25 characters"
            raise ValueError(error)

        if re.fullmatch(r"^[-\w]+$", self.slug) is None:
            error = "Slug can only contain letters, digits, underscores, and hyphens"

            raise ValueError(error)

        return self

    def perform_extra_deserialization(self, is_update, obj):
        if self.facility:
            obj.facility = get_object_or_404(Facility, external_id=self.facility)


class ReportTemplateUpdateSpec(ReportTemplateBaseSpec):
    config: ReportConfig


class ReportTemplateReadSpec(ReportTemplateBaseSpec):
    config: dict
    facility: dict | None = None
    slug: str
    type: str
    derived_from_url: str | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        if obj.facility:
            mapping["facility"] = (
                FacilityRetrieveSpec.serialize(obj.facility).to_json()
                if obj.facility
                else None
            )


class ReportTemplateRetrieveSpec(ReportTemplateReadSpec):
    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        if obj.created_by:
            mapping["created_by"] = UserSpec.serialize(obj.created_by).to_json()
        if obj.updated_by:
            mapping["updated_by"] = UserSpec.serialize(obj.updated_by).to_json()
