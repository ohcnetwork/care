from enum import Enum
from typing import Literal

from pydantic import UUID4, BaseModel, HttpUrl, model_validator

from care.emr.resources.base import EMRResource
from care.emr.resources.facility.spec import FacilityRetrieveSpec
from care.emr.resources.user.spec import UserSpec
from care.facility.models import FacilityReportTemplate


class PageMargin(BaseModel):
    mode: str
    value: str


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


class FacilityHeading(BaseModel):
    align: Literal["left", "center", "right"]
    size: str
    weight: str


class Divider(BaseModel):
    length: str
    stroke: str


class SummaryTitle(BaseModel):
    text: str
    size: str


class LogoConfig(BaseModel):
    file_name: str


class CreatedOn(BaseModel):
    label: str
    style: dict[Literal["fill", "weight"], str | int]
    date_format: str


class StyleConfig(BaseModel):
    fill: str | None
    weight: int | None


class TextElement(BaseModel):
    type: Literal["text"]
    text: str
    size: str
    weight: int
    align: Literal["left", "center", "right"] | None


class ImageElement(BaseModel):
    type: Literal["image"]
    file_name: str
    url: HttpUrl
    width: str | None
    align: Literal["left", "center", "right"] | None


class RuleElement(BaseModel):
    type: Literal["rule"]
    length: str = "100%"
    stroke: str | None = "black"
    align: Literal["left", "center", "right"] | None


class DateTimeElement(BaseModel):
    type: Literal["datetime"]
    label: str
    format: str
    style: StyleConfig
    align: Literal["left", "center", "right"] | None


HeaderElement = TextElement | ImageElement | RuleElement | DateTimeElement


class HeaderConfig(BaseModel):
    rows: list[list[HeaderElement]]


class SectionOptions(BaseModel):
    title: str | None
    fields: list[str] = []
    columns: list[str] = []
    style: Literal["list", "text"] | None = "list"
    filters: dict[str, list[str]] | None = []


class SectionConfig(BaseModel):
    source: str
    is_table: bool
    enabled: bool
    options: SectionOptions

    @model_validator(mode="after")
    def validate_table_config(self):
        if not self.is_table and not self.options.fields:
            raise ValueError("Field list is required for non-table sections")
        if self.is_table and not self.options.columns:
            raise ValueError("Column list is required for table sections")
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
        mapping["facility"] = FacilityRetrieveSpec.serialize(obj.facility)


class FacilityReportTemplateRetrieveSpec(FacilityReportTemplateReadSpec):
    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        if obj.created_by:
            mapping["created_by"] = UserSpec.serialize(obj.created_by).to_json()
        if obj.updated_by:
            mapping["updated_by"] = UserSpec.serialize(obj.updated_by).to_json()
