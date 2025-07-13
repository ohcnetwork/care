from enum import Enum

from pydantic import BaseModel, RootModel, model_validator

from care.emr.resources.common.coding import Coding


class MonetaryComponentType(str, Enum):
    base = "base"
    surcharge = "surcharge"
    discount = "discount"
    tax = "tax"
    informational = "informational"


class MonetaryComponent(BaseModel):
    monetary_component_type: MonetaryComponentType
    code: Coding | None = None
    factor: float | None = None
    amount: float | None = None

    @model_validator(mode="after")
    def base_no_factor(self):
        if (
            self.monetary_component_type == MonetaryComponentType.base.value
            and not self.amount
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
        if not ((self.amount is not None) or self.factor):
            raise ValueError("Either 'amount' or 'factor' must be present.")
        return self


class MonetaryComponents(RootModel):
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
