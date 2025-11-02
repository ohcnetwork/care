from enum import Enum

from pydantic import BaseModel


class PartnerType(str, Enum):
    person = "person"
    company = "company"


class PartnerData(BaseModel):
    name: str
    x_care_id: str
    email: str
    phone: str
    state: str
    partner_type: PartnerType
    agent: bool
    pan: str | None = None
