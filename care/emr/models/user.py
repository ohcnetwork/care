from django.db import models

from care.emr.models.base import BaseFlag
from care.utils.registries.feature_flag import FlagName, FlagType


class UserFlag(BaseFlag):
    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, null=False, blank=False
    )

    cache_key_template = "user_flag_cache:{entity_id}:{flag_name}"
    all_flags_cache_key_template = "user_all_flags_cache:{entity_id}"
    flag_type = FlagType.USER.value
    entity_field_name = "user"

    def __str__(self):
        return f"User Flag: {self.user.get_full_name()} - {self.flag}"

    class Meta:
        verbose_name = "User Flag"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "flag"],
                condition=models.Q(deleted=False),
                name="emr_unique_user_flag",
            )
        ]

    @classmethod
    def check_user_has_flag(cls, user_id: int, flag_name: FlagName) -> bool:
        return cls.check_entity_has_flag(user_id, flag_name)

    @classmethod
    def get_all_flags(cls, user_id: int) -> tuple[FlagName]:
        return super().get_all_flags(user_id)
