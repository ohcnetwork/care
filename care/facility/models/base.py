from care.users.models import User
from care.utils.models.base import BaseModel

READ_ONLY_USER_TYPES = [
    User.TYPE_VALUE_MAP["DistrictReadOnlyAdmin"],
    User.TYPE_VALUE_MAP["StateReadOnlyAdmin"],
    User.TYPE_VALUE_MAP["StaffReadOnly"],
]


def pretty_boolean(val, a="YES", b="NO", c="Not Specified"):
    if val is None:
        return c
    if val:
        return a
    return b


def reverse_choices(choices):
    output = {}
    for choice in choices:
        output[choice[0]] = choice[1]
    return output


def covert_choice_dict(choices):
    output = {}
    for choice in choices:
        output[choice[1]] = choice[0]
    return output


class FacilityBaseModel(BaseModel):
    class Meta:
        abstract = True


class PatientBaseModel(BaseModel):
    class Meta:
        abstract = True
