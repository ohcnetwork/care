import tempfile
from enum import Enum
from pathlib import Path
from typing import Annotated, Literal

import magic
import requests
from django.conf import settings
from pydantic import (
    UUID4,
    BaseModel,
    Field,
    HttpUrl,
    model_validator,
)

from care.emr.models.template import FacilityReportTemplate
from care.emr.resources.base import EMRResource
from care.emr.resources.facility.spec import FacilityRetrieveSpec
from care.emr.resources.user.spec import UserSpec


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
    fill: str | None = None
    weight: int | None = None


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
    length: str = "100%"
    stroke: str | None = "black"


class DateTimeElement(BaseModel):
    type: Literal["datetime"]
    label: str
    format: str
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
        return self


class ReportConfig(BaseModel):
    layout: Layout
    header: HeaderConfig
    sections: list[SectionConfig]


class FacilityReportTemplateTypes(str, Enum):
    discharge_summary = "discharge_summary"
    lab_report = "lab_report"


class FacilityReportTemplateBaseSpec(EMRResource):
    id: UUID4 | None = None

    __model__ = FacilityReportTemplate
    __exclude__ = ["facility"]


class FacilityReportTemplateCreateSpec(FacilityReportTemplateBaseSpec):
    config: ReportConfig
    slug: str | None = Field(None, min_length=5, max_length=25, pattern=r"^[-\w]+$")
    type: FacilityReportTemplateTypes


class FacilityReportTemplateUpdateSpec(FacilityReportTemplateBaseSpec):
    config: ReportConfig


class FacilityReportTemplateReadSpec(FacilityReportTemplateBaseSpec):
    config: dict
    facility: dict
    slug: str
    type: str

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["facility"] = FacilityRetrieveSpec.serialize(obj.facility).to_json()


class FacilityReportTemplateRetrieveSpec(FacilityReportTemplateReadSpec):
    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        if obj.created_by:
            mapping["created_by"] = UserSpec.serialize(obj.created_by).to_json()
        if obj.updated_by:
            mapping["updated_by"] = UserSpec.serialize(obj.updated_by).to_json()
