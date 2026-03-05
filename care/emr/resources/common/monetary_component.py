from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, RootModel, model_validator

from care.emr.resources.common.coding import Coding
from care.emr.resources.common.condition_evaluator import EvaluatorConditionSpec


class MonetaryComponentType(str, Enum):
    base = "base"
    surcharge = "surcharge"
    discount = "discount"
    tax = "tax"
    informational = "informational"


class MonetaryComponent(BaseModel):
    monetary_component_type: MonetaryComponentType
    code: Coding | None = None
    factor: Decimal | None = Field(default=None, max_digits=20, decimal_places=6)
    amount: Decimal | None = Field(default=None, max_digits=20, decimal_places=6)
    tax_included_amount: Decimal | None = Field(
        default=None, max_digits=20, decimal_places=6
    )
    global_component: bool = False
    conditions: list[EvaluatorConditionSpec] = []

    @model_validator(mode="after")
    def check_tax_included_amount(self):
        if (
            self.tax_included_amount is not None
            and self.monetary_component_type != MonetaryComponentType.base.value
        ):
            raise ValueError("Tax included amount is only allowed for base component.")
        return self

    @model_validator(mode="after")
    def base_no_conditions(self):
        if (
            self.monetary_component_type == MonetaryComponentType.base.value
            and self.conditions
        ):
            raise ValueError("Base component must have no conditions.")
        return self

    @model_validator(mode="after")
    def base_no_factor(self):
        if (
            self.monetary_component_type == MonetaryComponentType.base.value
            and self.amount is None
        ):
            raise ValueError("Base component must have an amount.")
        return self

    @model_validator(mode="after")
    def check_amount_and_factor(self):
        if self.factor and (self.amount is not None):
            raise ValueError(
                "Only one of 'amount' or 'factor' can be present, not both."
            )
        return self

    @model_validator(mode="after")
    def check_amount_or_factor(self):
        if self.global_component and self.code:
            return self
        if not ((self.amount is not None) or self.factor):
            raise ValueError("Either 'amount' or 'factor' must be present.")
        return self


class MonetaryComponentsWithoutBase(RootModel):
    root: list[MonetaryComponent] = []

    def __iter__(self):
        return iter(self.root)

    @model_validator(mode="after")
    def check_duplicate_codes(self):
        codes = [component.code.code for component in self.root if component.code]
        if len(codes) != len(set(codes)):
            raise ValueError("Duplicate codes are not allowed.")
        return self

    @model_validator(mode="after")
    def check_tax_included_amount_and_amount(self):
        base_price_component = None
        tax_components = []
        for component in self.root:
            if component.monetary_component_type == MonetaryComponentType.base.value:
                base_price_component = component
            elif component.monetary_component_type == MonetaryComponentType.tax.value:
                tax_components.append(component)
        if not base_price_component:
            return self
        if base_price_component.tax_included_amount is None:
            return self
        total_tax = Decimal(0)
        for component in tax_components:
            if component.amount is not None:
                total_tax += component.amount
            elif component.factor is not None:
                total_tax += base_price_component.amount * component.factor
        if (
            total_tax + base_price_component.tax_included_amount
            != base_price_component.amount
        ):
            raise ValueError(
                "Total tax amount must be equal to base price component amount."
            )
        return self


class MonetaryComponents(MonetaryComponentsWithoutBase):
    @model_validator(mode="after")
    def check_single_base_component(self):
        component_types = [component.monetary_component_type for component in self.root]
        if component_types.count(MonetaryComponentType.base) > 1:
            raise ValueError("Only one base component is allowed.")
        return self


class MonetaryComponentDefinition(MonetaryComponent):
    title: str

    @model_validator(mode="after")
    def check_duplicate_codes(self):
        # Override during definition
        return self

    @model_validator(mode="after")
    def check_amount_or_factor(self):
        # Override during definition
        return self

    @model_validator(mode="after")
    def check_base_absent(self):
        if self.monetary_component_type == MonetaryComponentType.base.value:
            raise ValueError("Base component is not allowed in definition.")
        return self


class DiscountApplicability(str, Enum):
    total_asc = "total_asc"
    total_desc = "total_desc"


class DiscountConfiguration(BaseModel):
    max_applicable: int = Field(ge=0)
    applicability_order: DiscountApplicability
