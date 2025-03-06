from pydantic import BaseModel, ConfigDict


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


class ValueSetInclude(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: str | None = None
    system: str | None = None
    version: str | None = None
    concept: list[ValueSetConcept] | None = None
    filter: list[ValueSetFilter] | None = None


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
