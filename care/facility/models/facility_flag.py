from django.db import models

from care.utils.models.base import BaseFlag
from care.utils.registries.feature_flag import FlagName, FlagType

FACILITY_FLAG_CACHE_KEY = "facility_flag_cache:{facility_id}:{flag_name}"
FACILITY_ALL_FLAGS_CACHE_KEY = "facility_all_flags_cache:{facility_id}"
FACILITY_FLAG_CACHE_TTL = 60 * 60 * 24  # 1 Day


class FacilityFlag(BaseFlag):
    facility = models.ForeignKey(
        "facility.Facility", on_delete=models.CASCADE, null=False, blank=False
    )

    cache_key_template = "facility_flag_cache:{entity_id}:{flag_name}"
    all_flags_cache_key_template = "facility_all_flags_cache:{entity_id}"
    flag_type = FlagType.FACILITY
    entity_field_name = "facility"

    def __str__(self) -> str:
        return f"Facility Flag: {self.facility.name} - {self.flag}"

    class Meta:
        verbose_name = "Facility Flag"
        constraints = [
            models.UniqueConstraint(
                fields=["facility", "flag"],
                condition=models.Q(deleted=False),
                name="unique_facility_flag",
            )
        ]

    @classmethod
    def check_facility_has_flag(cls, facility_id: int, flag_name: FlagName) -> bool:
        return cls.check_entity_has_flag(facility_id, flag_name)

    @classmethod
    def get_all_flags(cls, facility_id: int) -> tuple[FlagName]:
        return super().get_all_flags(facility_id)
