from enum import Enum

from pydantic import BaseModel

from care.emr.registries.care_valueset.care_valueset import CareValueset
from care.emr.resources.base import PeriodSpec
from care.emr.resources.common.valueset import ValueSetCompose
from care.emr.resources.valueset.spec import ValueSetStatusOptions
from care.emr.utils.valueset_coding_type import ValueSetBoundCoding

CARE_IDENTIFIER_VALUESET = CareValueset(
    "Identifier", "system-identifier", ValueSetStatusOptions.active.value
)

# TODO: update valuset
CARE_IDENTIFIER_VALUESET.register_valueset(
    ValueSetCompose(include=[{"system": "http://snomed.info/sct"}])
)
CARE_IDENTIFIER_VALUESET.register_as_system()


class IdnetifierUseChoices(str, Enum):
    usual = "usual"
    official = "official"
    temp = "temp"
    secondary = "secondary"
    old = "old"


class IdentifierSpec(BaseModel):
    use: IdnetifierUseChoices | None = None
    type: ValueSetBoundCoding[CARE_IDENTIFIER_VALUESET.slug] | None = None
    value: str
    period: PeriodSpec | None = None
    assigner: dict | None = None
