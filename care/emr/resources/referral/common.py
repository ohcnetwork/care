from enum import Enum

from rest_framework.exceptions import ValidationError

from care.emr.resources.base import model_from_cache
from care.emr.resources.user.spec import UserSpec
from care.users.models import User


class ReferralEntityType(str, Enum):
    external_organization = "external_organization"
    internal_organization = "internal_organization"
    facility = "facility"
    external = "external"


class ReferralAvailabilityStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    draft = "draft"


class ReferralType(str, Enum):
    consultation = "consultation"
    lab = "lab"


class ReferralQuestionnaireType(str, Enum):
    request = "request"
    response = "response"


def deserialize_care_team(members):
    user_ids = [member.user_id for member in members]
    if len(set(user_ids)) != len(user_ids):
        raise ValidationError("Care team users must be unique")
    users = {
        user.external_id: user.id
        for user in User.objects.filter(external_id__in=user_ids, is_active=True)
    }
    if len(users) != len(user_ids):
        raise ValidationError("Care team user not found or inactive")
    return [
        {"user_id": users[member.user_id], "role": member.role.model_dump(mode="json")}
        for member in members
    ]


def serialize_care_team(members):
    return [
        {
            "member": model_from_cache(UserSpec, id=member["user_id"]),
            "role": member["role"],
        }
        for member in members
    ]
