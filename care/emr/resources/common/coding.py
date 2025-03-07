from pydantic import BaseModel, ConfigDict


class Coding(BaseModel):
    """Represents a code from a code system"""

    model_config = ConfigDict(
        extra="forbid",
    )
    system: str | None = None
    version: str | None = None
    code: str
    display: str | None = None
