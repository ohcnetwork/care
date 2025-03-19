from pydantic import BaseModel, ConfigDict

from .coding import Coding


class CodeableConcept(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: str | None = None
    coding: list[Coding] | None = None
    text: str | None
