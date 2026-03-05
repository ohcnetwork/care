from typing import Literal

from django.conf import settings
from django.db.models.functions import Lower, Trim
from pydantic import UUID4, BaseModel, Field, field_validator, model_validator
from pydantic_core.core_schema import ValidationInfo
from pydantic_extra_types.coordinate import Latitude, Longitude

from care.emr.models import Organization
from care.emr.models.facility_config import FacilityMonetoryConfig
from care.emr.models.patient import PatientIdentifierConfigCache
from care.emr.resources.base import EMRResource, cacheable, model_from_cache
from care.emr.resources.common.coding import Coding
from care.emr.resources.common.monetary_component import (
    DiscountConfiguration,
    MonetaryComponentDefinition,
)
from care.emr.resources.invoice.default_expression_evaluator import (
    evaluate_invoice_dummy_expression,
)
from care.emr.resources.organization.spec import OrganizationReadSpec
from care.emr.resources.permissions import FacilityPermissionsMixin
from care.facility.models import (
    REVERSE_FACILITY_TYPES,
    REVERSE_REVERSE_FACILITY_TYPES,
    Facility,
)


@cacheable(use_base_manager=True)
class FacilityBareMinimumSpec(EMRResource):
    __model__ = Facility
    __exclude__ = ["geo_organization"]
    id: UUID4 | None = None
    name: str


class PageMargin(BaseModel):
    top: float = Field(ge=0)
    bottom: float = Field(ge=0)
    left: float = Field(ge=0)
    right: float = Field(ge=0)


class PageConfig(BaseModel):
    size: Literal["A4", "A5", "Letter", "Legal"] | None = None
    orientation: Literal["portrait", "landscape"] | None = None
    margin: PageMargin | None = None


class PrintSetupConfig(BaseModel):
    auto_print: bool | None = None


class LogoConfig(BaseModel):
    url: str
    width: float | None = None
    height: float | None = None
    alignment: Literal["left", "center", "right"]


class HeaderImageConfig(BaseModel):
    url: str
    height: float | None = None


class FooterImageConfig(BaseModel):
    url: str | None = None
    height: float | None = None


class BrandingConfig(BaseModel):
    logo: LogoConfig | None = None
    header_image: HeaderImageConfig | None = None
    footer_image: FooterImageConfig | None = None


class WatermarkConfig(BaseModel):
    enabled: bool | None = None
    text: str | None = None
    opacity: float | None = Field(None, ge=0, le=1)
    rotation: float | None = None


class PrintTemplate(BaseModel):
    slug: str
    page: PageConfig | None = None
    print_setup: PrintSetupConfig | None = None
    branding: BrandingConfig | None = None
    watermark: WatermarkConfig | None = None


class FacilityBaseSpec(FacilityBareMinimumSpec):
    description: str
    longitude: Longitude | None = None
    latitude: Latitude | None = None
    pincode: int
    address: str
    phone_number: str
    middleware_address: str | None = None
    facility_type: str
    is_public: bool


DISCOUNT_CODE_COUNT_LIMIT = 100
DISCOUNT_MONETARY_COMPONENT_COUNT_LIMIT = 100


class FacilityInvoiceExpressionSpec(BaseModel):
    invoice_number_expression: str

    @field_validator("invoice_number_expression")
    @classmethod
    def validate_invoice_number_expression(cls, v):
        if v:
            try:
                evaluate_invoice_dummy_expression(v)
            except Exception as e:
                err = "Invalid Expression"
                raise ValueError(err) from e
        return v


class FacilityCreateSpec(FacilityBaseSpec):
    geo_organization: UUID4
    features: list[int]
    print_templates: list[PrintTemplate] = []

    @field_validator("name")
    @classmethod
    def validate_name_uniqueness(cls, v, info: ValidationInfo):
        if not v:
            return v

        normalized_name = v.strip().lower()
        context = info.context or {}
        is_update = context.get("is_update", False)
        obj = context.get("object")

        qs = Facility.objects.annotate(normalized_name=Lower(Trim("name"))).filter(
            normalized_name=normalized_name
        )

        if is_update and obj:
            qs = qs.exclude(id=obj.id)

        if qs.exists():
            err = "A facility with this name already exists"
            raise ValueError(err)

        return v

    def perform_extra_deserialization(self, is_update, obj):
        obj.geo_organization = Organization.objects.filter(
            external_id=self.geo_organization, org_type="govt"
        ).first()
        obj.facility_type = REVERSE_REVERSE_FACILITY_TYPES[self.facility_type]


class FacilityReadSpec(FacilityBaseSpec):
    features: list[int]
    cover_image_url: str
    read_cover_image_url: str
    geo_organization: dict = {}
    created_by: dict = {}

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        from care.emr.resources.user.spec import UserSpec

        mapping["id"] = obj.external_id
        mapping["read_cover_image_url"] = obj.read_cover_image_url()
        if obj.created_by:
            mapping["created_by"] = model_from_cache(UserSpec, id=obj.created_by_id)
        mapping["facility_type"] = REVERSE_FACILITY_TYPES[obj.facility_type]
        if obj.geo_organization:
            mapping["geo_organization"] = OrganizationReadSpec.serialize(
                obj.geo_organization
            ).to_json()


class FacilityRetrieveSpec(FacilityReadSpec, FacilityPermissionsMixin):
    flags: list[str] = []
    discount_codes: list[dict] = []
    discount_monetary_components: list[dict] = []
    discount_configuration: dict | None = None

    instance_discount_codes: list[dict] = []
    instance_discount_monetary_components: list[dict] = []
    instance_tax_codes: list[dict] = []
    instance_tax_monetary_components: list[dict] = []
    instance_informational_codes: list[dict] = []
    # Identifiers
    patient_instance_identifier_configs: list[dict] = []
    patient_facility_identifier_configs: list[dict] = []
    invoice_number_expression: str | None = None

    print_templates: list[dict] = []

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        from care.emr.models.facility_config import FacilityMonetoryConfig

        super().perform_extra_serialization(mapping, obj)
        facility_monetory_config = FacilityMonetoryConfig.get_monetory_config(obj.id)

        mapping["invoice_number_expression"] = (
            facility_monetory_config.invoice_number_expression
        )
        mapping["discount_codes"] = facility_monetory_config.discount_codes
        mapping["discount_monetary_components"] = (
            facility_monetory_config.discount_monetary_components
        )
        mapping["discount_configuration"] = (
            facility_monetory_config.discount_configuration
        )

        mapping["flags"] = obj.get_facility_flags()
        mapping["instance_discount_codes"] = settings.DISCOUNT_CODES
        mapping["instance_discount_monetary_components"] = (
            settings.DISCOUNT_MONETARY_COMPONENT_DEFINITIONS
        )
        mapping["instance_tax_codes"] = settings.TAX_CODES
        mapping["instance_tax_monetary_components"] = (
            settings.TAX_MONETARY_COMPONENT_DEFINITIONS
        )
        mapping["patient_instance_identifier_configs"] = (
            PatientIdentifierConfigCache.get_instance_config()
        )
        mapping["patient_facility_identifier_configs"] = (
            PatientIdentifierConfigCache.get_facility_config(obj.id)
        )
        mapping["instance_informational_codes"] = settings.INFORMATIONAL_MONETARY_CODES


class FacilityMonetaryCodeSpec(EMRResource):
    __model__ = FacilityMonetoryConfig
    __exclude__ = []

    discount_codes: list[Coding]
    discount_monetary_components: list[MonetaryComponentDefinition]
    discount_configuration: DiscountConfiguration | None

    @model_validator(mode="after")
    def validate_count(self):
        if len(self.discount_codes) >= DISCOUNT_CODE_COUNT_LIMIT:
            raise ValueError("Discount codes cannot be more than 100.")
        if (
            len(self.discount_monetary_components)
            >= DISCOUNT_MONETARY_COMPONENT_COUNT_LIMIT
        ):
            raise ValueError("Discount monetary components cannot be more than 100.")
        return self

    @model_validator(mode="after")
    def validate_codes(self):
        # Duplicate codes are not allowed
        codes = [code.code for code in self.discount_codes]
        if len(codes) != len(set(codes)):
            raise ValueError("Duplicate codes are not allowed.")
        # Redefining system codes are not allowed
        system_codes = [[code.code, code.system] for code in settings.DISCOUNT_CODES]
        for code in self.discount_codes:
            if [code.code, code.system] in system_codes:
                raise ValueError("Redefining system codes are not allowed.")
        # All monetary components code must be defined
        facility_codes = [[code.code, code.system] for code in self.discount_codes]
        all_allowed_codes = system_codes + facility_codes
        for definition in self.discount_monetary_components:
            if (
                definition.code
                and [
                    definition.code.code,
                    definition.code.system,
                ]
                not in all_allowed_codes
            ):
                raise ValueError("All monetary components code must be defined.")
        return self


class FacilityMinimalReadSpec(FacilityBaseSpec):
    features: list[int]
    cover_image_url: str
    read_cover_image_url: str
    geo_organization: dict = {}

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["read_cover_image_url"] = obj.read_cover_image_url()
        mapping["facility_type"] = REVERSE_FACILITY_TYPES[obj.facility_type]
        if obj.geo_organization:
            mapping["geo_organization"] = OrganizationReadSpec.serialize(
                obj.geo_organization
            ).to_json()
