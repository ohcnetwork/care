from enum import Enum
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator


class ValueSetConcept(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: str | None = None

    code: str | None = None
    display: str | None = None


class FilterOperatorOptions(str, Enum):
    equal = "="
    is_a = "is-a"
    descendent_of = "descendent-of"
    is_not_a = "is-not-a"
    regex = "regex"
    in_ = "in"  # 'in' is a Python keyword, so use 'in_'
    not_in = "not-in"
    generalizes = "generalizes"
    child_of = "child-of"
    descendent_leaf = "descendent-leaf"
    exists = "exists"


class ValueSetFilter(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: str | None = None

    property: str | None = None
    op: FilterOperatorOptions
    value: str | None = None


class ValueSetInclude(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: str | None = None
    system: str | None = None
    version: str | None = None
    concept: list[ValueSetConcept] | None = None
    filter: list[ValueSetFilter] | None = None

    @model_validator(mode="after")
    def check_concept_or_filter(self) -> Self:
        if self.concept and self.filter:
            raise ValueError(
                "Only one of 'concept' or 'filter' can be present, not both."
            )
        return self


class ValueSetCompose(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: str | None = None
    include: list[ValueSetInclude]
    exclude: list[ValueSetInclude] | None = None
    property: list[str] | None = None


class ValueSet(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    name: str
    status: str | None = None
    compose: ValueSetCompose
