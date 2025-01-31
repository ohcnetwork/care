from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from care.emr.resources.common import Coding  # noqa TCH001


class Quantity(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    value: float | None = Field(
        None,
        description="The value of the measured amount. The value includes an implicit precision in the presentation of the value.",
    )
    unit: Coding | None = Field(None, description="A human-readable form of the unit.")
    meta: dict | None = Field(None)
    code: Coding | None = Field(
        None,
        description="A computer processable form of the unit in some unit representation system.",
    )
