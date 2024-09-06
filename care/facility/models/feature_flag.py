from care.facility.registries.feature_flag import FlagRegistry, FlagType
from care.utils.models.base import BaseModel

from django.db import models


class FacilityFlag(BaseModel):
    facility = models.ForeignKey(
        "Facility", on_delete=models.CASCADE, null=False, blank=False
    )
    flag = models.CharField(max_length=1024)

    class Meta:
        verbose_name = "Facility Flag"

    def __str__(self):
        return f"{self.facility.name} - {self.flag}"

    @classmethod
    def validate_flag(cls, flag_name):
        FlagRegistry.validate_flag_name(FlagType.FACILITY, flag_name)

    def save(
        self, *args, **kwargs
    ):
        self.validate_flag(self.flag)
        # TODO : Add Unique Together
        return super().save(*args, **kwargs)

    @classmethod
    def check_facility_has_flag(cls , facility , flag_name):
        cls.validate_flag(flag_name)
        # TODO : Add Caching , Invalidate on save actions
        return cls.objects.filter(facility=facility, flag=flag_name).exists()
