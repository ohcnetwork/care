from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import models

from care.utils.models.base import BaseModel
from care.utils.registries.feature_flag import FlagName, FlagRegistry, FlagType

FACILITY_FLAG_CACHE_KEY = "facility_flag_cache:{facility_id}:{flag_name}"
FACILITY_ALL_FLAGS_CACHE_KEY = "facility_all_flags_cache:{facility_id}"
FACILITY_FLAG_CACHE_TTL = 60 * 60 * 24  # 1 Day


class FacilityFlag(BaseModel):
    facility = models.ForeignKey(
        "facility.Facility", on_delete=models.CASCADE, null=False, blank=False
    )
    flag = models.CharField(max_length=1024)

    @classmethod
    def validate_flag(cls, flag_name: FlagName):
        FlagRegistry.validate_flag_name(FlagType.FACILITY, flag_name)

    def save(self, *args, **kwargs):
        self.validate_flag(self.flag)

        if (
            not self.deleted
            and self.__class__.objects.filter(
                facility_id=self.facility_id, flag=self.flag
            ).exists()
        ):
            raise ValidationError("Flag Already Exists")

        cache.delete(
            FACILITY_FLAG_CACHE_KEY.format(
                facility_id=self.facility_id, flag_name=self.flag
            )
        )
        cache.delete(FACILITY_ALL_FLAGS_CACHE_KEY.format(facility_id=self.facility_id))

        return super().save(*args, **kwargs)

    @classmethod
    def check_facility_has_flag(cls, facility_id: int, flag_name: FlagName) -> bool:
        cls.validate_flag(flag_name)
        return cache.get_or_set(
            FACILITY_FLAG_CACHE_KEY.format(
                facility_id=facility_id, flag_name=flag_name
            ),
            default=lambda: cls.objects.filter(
                facility_id=facility_id, flag=flag_name
            ).exists(),
            timeout=FACILITY_FLAG_CACHE_TTL,
        )

    @classmethod
    def get_all_flags(cls, facility_id: int) -> tuple[FlagName]:
        return cache.get_or_set(
            FACILITY_ALL_FLAGS_CACHE_KEY.format(facility_id=facility_id),
            default=lambda: tuple(
                cls.objects.filter(facility_id=facility_id).values_list(
                    "flag", flat=True
                )
            ),
            timeout=FACILITY_FLAG_CACHE_TTL,
        )

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
