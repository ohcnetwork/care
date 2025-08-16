from pydantic import BaseModel, RootModel, model_validator

from care.emr.resources.common.coding import Coding
from care.emr.resources.common.monetary_component import MonetaryComponentDefinition


class MonetaryCodes(RootModel):
    root: list[Coding] = []

    def __iter__(self):
        return iter(self.root)

    @model_validator(mode="after")
    def check_duplicate_codes(self):
        codes = [code.code for code in self.root]
        if len(codes) != len(set(codes)):
            raise ValueError("Duplicate codes are not allowed.")
        return self


class MonetaryComponentDefinitions(RootModel):
    root: list[MonetaryComponentDefinition] = []
