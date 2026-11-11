from datetime import date
from itertools import pairwise

from pydantic import UUID4, BaseModel, Field, RootModel, model_validator
from pydantic.experimental.missing_sentinel import MISSING

from care.emr.models.immunisation import ImmunizationPolicy
from care.emr.resources.base import EMRResource
from care.emr.resources.immunisation.recommendation import (
    BaseImmunizationRecommendationSpec,
    ImmunizationRecommendationRetrieveSpec,
)
from care.facility.models.facility import Facility
from care.utils.shortcuts import get_object_or_404


class ImmunizationPolicyTemplateSpec(BaseImmunizationRecommendationSpec):
    is_group: bool
    children: list["ImmunizationPolicyTemplateSpec"] = Field(default_factory=list)
    due_date: int | MISSING = Field(
        default=MISSING, description="Days from the reference date"
    )
    earliest_date: int | MISSING = Field(
        default=MISSING, description="Days from the reference date"
    )
    overdue_date: int | MISSING = Field(
        default=MISSING, description="Days from the reference date"
    )

    @model_validator(mode="after")
    def validate_only_groups_contain_children(self):
        if self.children and not self.is_group:
            raise ValueError("Only groups can contain children")
        return self

    @model_validator(mode="after")
    def validate_codes(self):
        if not self.is_group and (self.codes is MISSING or not self.codes):
            raise ValueError("Codes are required for non-group recommendations")
        return self

    @model_validator(mode="after")
    def validate_date_order(self):
        dates = [
            ("earliest_date", self.earliest_date),
            ("due_date", self.due_date),
            ("overdue_date", self.overdue_date),
        ]
        present = [(name, value) for name, value in dates if value is not MISSING]
        for (left_name, left_value), (right_name, right_value) in pairwise(present):
            if left_value >= right_value:
                err = f"{left_name} must be before {right_name}"
                raise ValueError(err)
        return self


class ImmunizationPolicySpec(EMRResource):
    __model__ = ImmunizationPolicy
    id: UUID4 | None = None
    policy_template: ImmunizationPolicyTemplateSpec
    name: str
    description: str | MISSING = MISSING


class ImmunizationPolicyCreateSpec(ImmunizationPolicySpec):
    facility: UUID4 | None = None

    def perform_extra_deserialization(self, is_update, obj):
        if self.facility:
            obj.facility = get_object_or_404(
                Facility.objects.only("id"), external_id=self.facility
            )
        return super().perform_extra_deserialization(is_update, obj)


class ImmunizationPolicyUpdateSpec(ImmunizationPolicySpec):
    pass


class ImmunizationPolicyListSpec(ImmunizationPolicySpec):
    pass


class ImmunizationPolicyRetrieveSpec(ImmunizationPolicySpec):
    pass


class ImmunizationPolicyApplySpec(BaseModel):
    policy: UUID4
    reference_date: date = Field(
        description="Date from which policy day offsets are calculated"
    )
    encounter: UUID4 | None = None
    parent: UUID4 | None = None


class ImmunizationPolicyApplyResponseSpec(
    RootModel[list[ImmunizationRecommendationRetrieveSpec]]
):
    pass


ImmunizationPolicyTemplateSpec.model_rebuild()
