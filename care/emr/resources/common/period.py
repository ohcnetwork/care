import datetime

from pydantic import BaseModel, model_validator


class PeriodSpec(BaseModel):
    start: datetime.datetime | None = None
    end: datetime.datetime | None = None

    @model_validator(mode="after")
    def validate_period(self):
        if (self.start and self.end) and (self.start > self.end):
            raise ValueError("Start Date cannot be greater than End Date")
        return self
