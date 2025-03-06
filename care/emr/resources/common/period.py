from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Period(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: str | None = None
    start: datetime | None = None
    end: datetime | None = None
