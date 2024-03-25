import datetime
from decimal import Decimal
from typing import TypedDict


class BpInner(TypedDict):
    systolic: int
    diastolic: int
    mean: int


class MewsType(TypedDict):
    resp: int
    bp: BpInner
    temperature: Decimal
    pulse: int
    consciousness_level: int
    modified_date: datetime.datetime
