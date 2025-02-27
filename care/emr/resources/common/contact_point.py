from enum import Enum

from pydantic import BaseModel


class ContactPointSystemChoices(str, Enum):
    phone = "phone"
    fax = "fax"
    email = "email"
    pager = "pager"
    url = "url"
    sms = "sms"
    other = "other"


class ContactPointUseChoices(str, Enum):
    home = "home"
    work = "work"
    temp = "temp"
    old = "old"
    mobile = "mobile"


class ContactPoint(BaseModel):
    system: ContactPointSystemChoices
    value: str
    use: ContactPointUseChoices
