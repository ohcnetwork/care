from pydantic import UUID4, field_validator

from care.emr.resources.base import EMRResource
from care.emr.resources.user.spec import UserSpec
from care.users.models import User, UserFlag
from care.utils.registries.feature_flag import FlagRegistry, FlagType
from care.utils.shortcuts import get_object_or_404


class UserFlagBaseSpec(EMRResource):
    __model__ = UserFlag
    __exclude__ = ["user"]

    id: UUID4 | None = None
    flag: str


class UserFlagCreateSpec(UserFlagBaseSpec):
    user: UUID4

    @field_validator("flag")
    @classmethod
    def validate_flag_name(cls, flag_name):
        FlagRegistry.validate_flag_name(FlagType.USER, flag_name)
        return flag_name

    def perform_extra_deserialization(self, is_update, obj):
        if not is_update:
            obj.user = get_object_or_404(User, external_id=self.user)


class UserFlagUpdateSpec(UserFlagBaseSpec):
    @field_validator("flag")
    @classmethod
    def validate_flag_name(cls, flag_name):
        FlagRegistry.validate_flag_name(FlagType.USER, flag_name)
        return flag_name


class UserFlagReadSpec(UserFlagBaseSpec):
    user: dict

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["user"] = UserSpec.serialize(obj.user).to_json()


class UserFlagRetrieveSpec(UserFlagReadSpec):
    pass
