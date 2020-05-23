from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models

from location_field.models.spatial import LocationField
from partial_index import PQ, PartialIndex
from simple_history.models import HistoricalRecords

from apps.accounts import models as common_accounts_models
from apps.commons import (
    models as commons_models,
    validators as commons_validators,
    constants as commons_constants,
)
from apps.facility import (
    constants as commons_facility_constants,
    validators as commons_facility_validators,
)


User = get_user_model()


class FacilityType(commons_models.SoftDeleteTimeStampedModel):
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.name}"


class Facility(commons_models.SoftDeleteTimeStampedModel):
    name = models.CharField(max_length=1000)
    facility_code = models.CharField(max_length=50)
    facility_type = models.ForeignKey(FacilityType, on_delete=models.CASCADE)
    owned_by = models.ForeignKey(commons_models.OwnershipType, on_delete=models.CASCADE)
    location = LocationField(based_fields=["address"], zoom=7, blank=True, null=True)
    address = models.TextField()
    local_body = models.ForeignKey(
        common_accounts_models.LocalBody,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    district = models.ForeignKey(
        common_accounts_models.District,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    state = models.ForeignKey(
        common_accounts_models.State, on_delete=models.SET_NULL, null=True, blank=True
    )
    phone_number = models.CharField(
        max_length=14, blank=True, validators=[commons_validators.phone_number_regex]
    )
    pincode = models.CharField(max_length=6)
    corona_testing = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    total_patient = models.PositiveIntegerField(default=0)
    positive_patient = models.PositiveIntegerField(default=0)
    negative_patient = models.PositiveIntegerField(default=0)

    users = models.ManyToManyField(
        User,
        through="FacilityUser",
        related_name="facilities",
        through_fields=("facility", "user"),
    )

    class Meta:
        verbose_name_plural = "Facilities"

    def __str__(self):
        return f"{self.name}"

    def save(self, *args, **kwargs) -> None:
        """
        While saving, if the local body is not null, then district will be local body's district
        Overriding save will help in a collision where the local body's district and district fields are different.
        """
        if self.local_body is not None:
            self.district = self.local_body.district
        if self.district is not None:
            self.state = self.district.state

        is_create = self.pk is None
        super().save(*args, **kwargs)

        if is_create:
            FacilityUser.objects.create(
                facility=self, user=self.created_by, created_by=self.created_by
            )


class StaffDesignation(models.Model):

    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class FacilityStaff(commons_models.SoftDeleteTimeStampedModel):
    facility = models.ForeignKey(
        "Facility", on_delete=models.CASCADE, null=False, blank=False
    )
    name = models.CharField(max_length=256)
    phone_number = models.CharField(max_length=15)
    email = models.EmailField(max_length=50)
    designation = models.ForeignKey(StaffDesignation, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return str(self.name) + " for facility " + str(self.facility)


class RoomType(models.Model):
    name = models.CharField(max_length=25)
    description = models.TextField(blank=True)

    def __str__(self):
        return str(self.name)


class BedType(models.Model):
    name = models.CharField(max_length=25)
    description = models.TextField(blank=True)

    def __str__(self):
        return str(self.name)


class FacilityInfrastructure(commons_models.SoftDeleteTimeStampedModel):
    facility = models.ForeignKey(
        "Facility", on_delete=models.CASCADE, null=False, blank=False
    )
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE)
    bed_type = models.ForeignKey(BedType, on_delete=models.CASCADE)
    total_bed = models.PositiveIntegerField(default=0)
    occupied_bed = models.PositiveIntegerField(default=0)
    available_bed = models.PositiveIntegerField(default=0)


class InventoryItem(commons_models.SoftDeleteTimeStampedModel):
    name = models.CharField(max_length=256)
    description = models.TextField()
    unit = models.CharField(max_length=20)

    def __str__(self):
        return (
            self.name
            + " with unit "
            + self.unit
            + " with minimum stock "
        )


class Inventory(commons_models.SoftDeleteTimeStampedModel):
    facility = models.ForeignKey(
        "Facility", on_delete=models.CASCADE, null=False, blank=False
    )
    item = models.ForeignKey("InventoryItem", on_delete=models.CASCADE)
    required_quantity = models.PositiveIntegerField(default=0)
    current_quantity = models.PositiveIntegerField(default=0)

    history = HistoricalRecords()

    class Meta:
        verbose_name_plural = "Inventories"


class FacilityUser(commons_models.SoftDeleteTimeStampedModel):
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_incharge = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="created_users"
    )


class TestingLab(commons_models.SoftDeleteTimeStampedModel):
    """
    model for the lab associated with the patient sample test
    """

    LAB_TYPE_CHOICES = [
        (commons_facility_constants.LAB_TYPE_CHOICES.AC, "A1C"),
        (commons_facility_constants.LAB_TYPE_CHOICES.BC, "BLOOD COUNT TESTS"),
        (commons_facility_constants.LAB_TYPE_CHOICES.DI, "DIAGNOSTIC IMAGING"),
        (commons_facility_constants.LAB_TYPE_CHOICES.HT, "HEPATITIS TESTING"),
        (commons_facility_constants.LAB_TYPE_CHOICES.KT, "KIDNEY TESTS"),
        (commons_facility_constants.LAB_TYPE_CHOICES.TT, "THYROID TESTS"),
        (commons_facility_constants.LAB_TYPE_CHOICES.UL, "URINALYSIS"),
    ]
    name = models.CharField(
        max_length=commons_constants.FIELDS_CHARACTER_LIMITS["NAME"],
        help_text="Name of the Testing Lab",
    )
    address = models.TextField()
    lab_type = models.IntegerField(
        choices=LAB_TYPE_CHOICES, default=commons_facility_constants.LAB_TYPE_CHOICES.BC
    )
    district = models.ForeignKey(
        common_accounts_models.District, on_delete=models.PROTECT, related_name="labs",
    )

    def __str__(self):
        return f"{self.name}<>{self.district.name}"
