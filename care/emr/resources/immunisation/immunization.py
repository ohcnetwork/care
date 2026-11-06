from datetime import datetime
from enum import Enum

from pydantic import UUID4
from pydantic.experimental.missing_sentinel import MISSING

from care.emr.models.encounter import Encounter
from care.emr.models.immunisation import Immunization, ImmunizationRecommendation
from care.emr.models.location import FacilityLocation
from care.emr.models.product import Product
from care.emr.resources.base import EMRResource, model_from_cache
from care.emr.resources.common.quantity import Quantity
from care.emr.resources.medication.valueset.body_site import CARE_BODY_SITE_VALUESET
from care.emr.resources.medication.valueset.medication import CARE_MEDICATION_VALUESET
from care.emr.resources.medication.valueset.route import CARE_ROUTE_VALUESET
from care.emr.resources.user.spec import UserSpec
from care.emr.utils.valueset_coding_type import ValueSetBoundCoding
from care.users.models import User
from care.utils.shortcuts import get_object_or_404


class ImmunizationStatus(str, Enum):
    draft = "draft"
    completed = "completed"
    entered_in_error = "entered_in_error"
    not_done = "not_done"


class ImmunizationReason(str, Enum):
    IMMUNE = "IMMUNE"
    MEDPREC = "MEDPREC"
    OSTOCK = "OSTOCK"
    PATOBJ = "PATOBJ"
    PHILISOP = "PHILISOP"
    RELIG = "RELIG"
    VACEFF = "VACEFF"
    VACSAF = "VACSAF"


class BaseImmunizationSpec(EMRResource):
    __model__ = Immunization

    id: UUID4 | None = None
    status: ImmunizationStatus
    reason: ImmunizationReason | MISSING = MISSING
    code: ValueSetBoundCoding[CARE_MEDICATION_VALUESET.slug]
    occurrence: datetime | MISSING = MISSING
    primary_source: bool
    site: ValueSetBoundCoding[CARE_BODY_SITE_VALUESET.slug] | MISSING = MISSING
    route: ValueSetBoundCoding[CARE_ROUTE_VALUESET.slug] | MISSING = MISSING
    dose_quantity: Quantity | MISSING = MISSING
    note: str | MISSING = MISSING
    is_subpotent: bool | MISSING = MISSING
    subpotent_reason: str | MISSING = MISSING


class ImmunizationWriteSpec(BaseImmunizationSpec):
    recommendation: UUID4 | None | MISSING = MISSING
    product: UUID4 | None | MISSING = MISSING
    location: UUID4 | None | MISSING = MISSING
    administered_by: str | None | MISSING = MISSING

    def perform_extra_deserialization(self, is_update, obj):
        if self.recommendation is not MISSING:
            obj.recommendation = (
                get_object_or_404(
                    ImmunizationRecommendation.objects.filter(patient=obj.patient),
                    external_id=self.recommendation,
                )
                if self.recommendation is not None
                else None
            )
        if self.product is not MISSING:
            obj.product = (
                get_object_or_404(
                    Product.objects.filter(facility=obj.facility),
                    external_id=self.product,
                )
                if self.product is not None
                else None
            )
        if self.location is not MISSING:
            obj.location = (
                get_object_or_404(
                    FacilityLocation.objects.filter(facility=obj.facility),
                    external_id=self.location,
                )
                if self.location is not None
                else None
            )
        if self.administered_by is not MISSING:
            obj.administered_by = (
                get_object_or_404(User.objects, username=self.administered_by)
                if self.administered_by is not None
                else None
            )
        return super().perform_extra_deserialization(is_update, obj)


class ImmunizationCreateSpec(ImmunizationWriteSpec):
    encounter: UUID4

    def perform_extra_deserialization(self, is_update, obj):
        obj.encounter = get_object_or_404(Encounter.objects, external_id=self.encounter)
        obj.patient = obj.encounter.patient
        obj.facility = obj.encounter.facility
        return super().perform_extra_deserialization(is_update, obj)


class ImmunizationUpdateSpec(ImmunizationWriteSpec):
    status: ImmunizationStatus | MISSING = MISSING
    code: ValueSetBoundCoding[CARE_MEDICATION_VALUESET.slug] | MISSING = MISSING
    primary_source: bool | MISSING = MISSING


class ImmunizationListSpec(BaseImmunizationSpec):
    encounter: UUID4
    recommendation: UUID4 | None = None

    administered_by: UserSpec | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        mapping["encounter"] = obj.encounter.external_id
        mapping["recommendation"] = (
            obj.recommendation.external_id if obj.recommendation else None
        )
        mapping["administered_by"] = (
            model_from_cache(UserSpec, id=obj.administered_by_id)
            if obj.administered_by_id is not None
            else None
        )


class ImmunizationRetrieveSpec(ImmunizationListSpec):
    created_by: dict | None = None
    updated_by: dict | None = None
    product: UUID4 | None = None
    location: UUID4 | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        mapping["product"] = obj.product.external_id if obj.product else None
        mapping["location"] = obj.location.external_id if obj.location else None
        cls.serialize_audit_users(mapping, obj)
