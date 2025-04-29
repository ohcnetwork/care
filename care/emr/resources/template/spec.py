from enum import Enum
from typing import Literal

from pydantic import UUID4, BaseModel, HttpUrl, model_validator

from care.emr.resources.base import EMRResource
from care.emr.resources.facility.spec import FacilityRetrieveSpec
from care.emr.resources.user.spec import UserSpec
from care.facility.models import FacilityReportTemplate


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


class RuleElement(BaseModel):
    type: Literal["rule"]
    length: str = "100%"
    stroke: str | None = "black"
    align: Literal["left", "center", "right"] | None = None


class DateTimeElement(BaseModel):
    type: Literal["datetime"]
    label: str
    format: str
    style: StyleConfig
    align: Literal["left", "center", "right"] | None = None


HeaderElement = TextElement | ImageElement | RuleElement | DateTimeElement


class HeaderConfig(BaseModel):
    rows: list[list[HeaderElement]]


class LabelValueField(BaseModel):
    label: str
    value: str


class SectionOptions(BaseModel):
    title: str | None = None
    fields: list[str] | list[LabelValueField] = []
    columns: list[str] = []
    style: Literal["list", "text"] | None = "list"
    filters: dict[str, list[str]] | None = None
    text: str | None = None
    rows: list[list[str]] | None = None


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


class FacilityReportTemplateType(str, Enum):
    discharge_summary = "discharge_summary"
    lab_report = "lab_report"


class FacilityReportTemplateBaseSpec(EMRResource):
    id: UUID4 | None = None

    __model__ = FacilityReportTemplate
    __exclude__ = ["facility"]


class FacilityReportTemplateCreateSpec(FacilityReportTemplateBaseSpec):
    config: ReportConfig
    type: FacilityReportTemplateType


class FacilityReportTemplateUpdateSpec(FacilityReportTemplateBaseSpec):
    config: ReportConfig


class FacilityReportTemplateReadSpec(FacilityReportTemplateBaseSpec):
    config: dict
    facility: dict
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
