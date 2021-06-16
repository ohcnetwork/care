from uuid import uuid4

from django.core.validators import RegexValidator

from care.users.models import User

from care.utils.models.base import BaseModel

phone_number_regex = RegexValidator(
    regex=r"^((\+91|91|0)[\- ]{0,1})?[456789]\d{9}$",
    message="Please Enter 10/11 digit mobile number or landline as 0<std code><phone number>",
    code="invalid_mobile",
)

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


class FacilityBaseModel(BaseModel):
    class Meta:
        abstract = True


class PatientBaseModel(BaseModel):
    class Meta:
        abstract = True
