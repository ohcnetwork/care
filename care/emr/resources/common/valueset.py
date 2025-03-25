from typing import Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class ValueSetConcept(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: str | None = None
    code: str | None = None
    display: str | None = None


class ValueSetFilter(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: str | None = None

    property: str | None = None
    op: str | None = None
    value: str | None = None

    @field_validator("op")
    @classmethod
    def validate_op(cls, op: str | None, info):
        allowed_op = [
            "=",
            "is-a",
            "descendent-of",
            "is-not-a",
            "regex",
            "in",
            "not-in",
            "generalizes",
            "child-of",
            "descendent-leaf",
            "exists",
        ]
        if op is not None and op not in allowed_op:
            error = f"Invalid op value {op}. Allowed values are {allowed_op}"
            raise ValueError(error)
        return op


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
