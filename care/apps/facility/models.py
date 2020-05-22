from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models

from location_field.models.spatial import LocationField
from partial_index import PQ, PartialIndex
from simple_history.models import HistoricalRecords

from apps.accounts import (
    models as common_accounts_models
)
from apps.commons import (
    models as commons_models,
    validators as commons_validators
)
from apps.facility import (
    constants as commons_facility_constants,
    validators as commons_facility_validators,
)

User = get_user_model()


class Ambulance(commons_models.SoftDeleteTimeStampedModel):
    vehicle_number = models.CharField(max_length=20, validators=[commons_facility_validators.vehicle_number_regex], unique=True, db_index=True)
    owner_name = models.CharField(max_length=255)
    owner_phone_number = models.CharField(max_length=14, validators=[commons_validators.phone_number_regex])
    owner_is_smart_phone = models.BooleanField(default=True)
    primary_district = models.ForeignKey(
        common_accounts_models.District, on_delete=models.PROTECT, null=True, related_name="primary_ambulances"
    )
    secondary_district = models.ForeignKey(
        common_accounts_models.District, on_delete=models.PROTECT, blank=True, null=True, related_name="secondary_ambulances",
    )
    third_district = models.ForeignKey(
        common_accounts_models.District, on_delete=models.PROTECT, blank=True, null=True, related_name="third_ambulances",
    )
    has_oxygen = models.BooleanField()
    has_ventilator = models.BooleanField()
    has_suction_machine = models.BooleanField()
    has_defibrillator = models.BooleanField()
    insurance_valid_till_year = models.IntegerField(choices=commons_facility_constants.INSURANCE_YEAR_CHOICES)
    ambulance_type = models.IntegerField(choices=commons_facility_constants.AMBULANCE_TYPES, blank=False, default=1)

    price_per_km = models.DecimalField(max_digits=7, decimal_places=2, null=True)
    has_free_service = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    @property
    def drivers(self):
        return self.ambulancedriver_set.filter(active=True)

    def __str__(self):
        return f"Ambulance - {self.owner_name}({self.owner_phone_number})"

    class Meta:
        verbose_name_plural = "ambulances"

class AmbulanceDriver(commons_models.SoftDeleteTimeStampedModel):
    ambulance = models.ForeignKey(Ambulance, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=14, validators=[commons_validators.phone_number_regex])
    is_smart_phone = models.BooleanField()

    def __str__(self):
        return f"Driver: {self.name}({self.phone_number})"
    
    class Meta:
        verbose_name_plural = "AmbulancesDrivers"


class Facility(commons_models.SoftDeleteTimeStampedModel):
    name = models.CharField(max_length=1000, blank=False, null=False)
    is_active = models.BooleanField(default=True)
    verified = models.BooleanField(default=False)
    facility_type = models.IntegerField(choices=commons_facility_constants.FACILITY_TYPES)
    location = LocationField(based_fields=["address"], zoom=7, blank=True, null=True)
    address = models.TextField()
    local_body = models.ForeignKey(common_accounts_models.LocalBody, on_delete=models.SET_NULL, null=True, blank=True)
    district = models.ForeignKey(common_accounts_models.District, on_delete=models.SET_NULL, null=True, blank=True)
    state = models.ForeignKey(common_accounts_models.State, on_delete=models.SET_NULL, null=True, blank=True)
    oxygen_capacity = models.IntegerField(default=0)
    phone_number = models.CharField(max_length=14, blank=True, validators=[commons_validators.phone_number_regex])
    corona_testing = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    users = models.ManyToManyField(
        User, through="FacilityUser", related_name="facilities", through_fields=("facility", "user"),
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
            FacilityUser.objects.create(facility=self, user=self.created_by, created_by=self.created_by)


class FacilityLocalGovtBody(commons_models.SoftDeleteTimeStampedModel):
    """
    Model to relate a Facility to a local self governing body
    In ideal cases, the facility will be related to a local governing body.
    But in other cases, and in cases of incomplete data, we will only have information till a district level
    """

    facility = models.OneToOneField(Facility, unique=True, null=True, blank=True, on_delete=models.SET_NULL)
    local_body = models.ForeignKey(common_accounts_models.LocalBody, null=True, blank=True, on_delete=models.SET_NULL)
    district = models.ForeignKey(common_accounts_models.District, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="cons_facilitylocalgovtbody_only_one_null",
                check=models.Q(local_body__isnull=False) | models.Q(district__isnull=False),
            )
        ]

    def __str__(self):
        return (
            f"{getattr(self.local_body, 'name', '-')} "
            f"({getattr(self.local_body, 'localbody_type', '-')})"
            f" / {getattr(self.district, 'name', '-')}"
        )

    def save(self, *args, **kwargs) -> None:
        """
        While saving, if the local body is not null, then district will be local body's district
        Overriding save will help in a collision where the local body's district and district fields are different.
        """
        if self.local_body is not None:
            self.district = self.local_body.district
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name_plural = "FacilityLocalGovtBodies"


class HospitalDoctors(commons_models.SoftDeleteTimeStampedModel):
    facility = models.ForeignKey("Facility", on_delete=models.CASCADE, null=False, blank=False)
    area = models.IntegerField(choices=commons_facility_constants.DOCTOR_TYPES)
    count = models.IntegerField()

    def __str__(self):
        return str(self.facility) + str(self.count)

    class Meta:
        indexes = [PartialIndex(fields=["facility", "area"], unique=True, where=PQ(active=True))]


class FacilityCapacity(commons_models.SoftDeleteTimeStampedModel):
    facility = models.ForeignKey("Facility", on_delete=models.CASCADE, null=False, blank=False)
    room_type = models.IntegerField(choices=commons_facility_constants.ROOM_TYPES)
    total_capacity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    current_capacity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    history = HistoricalRecords()

    class Meta:
        indexes = [PartialIndex(fields=["facility", "room_type"], unique=True, where=PQ(active=True))]


class FacilityStaff(commons_models.SoftDeleteTimeStampedModel):
    facility = models.ForeignKey("Facility", on_delete=models.CASCADE, null=False, blank=False)
    staff = models.ForeignKey(User, on_delete=models.CASCADE, null=False, blank=False)

    def __str__(self):
        return str(self.staff) + " for facility " + str(self.facility)


class FacilityVolunteer(commons_models.SoftDeleteTimeStampedModel):
    facility = models.ForeignKey("Facility", on_delete=models.CASCADE, null=False, blank=False)
    volunteer = models.ForeignKey(User, on_delete=models.CASCADE, null=False, blank=False)

    def __str__(self):
        return str(self.volunteer) + " for facility " + str(self.facility)


class Building(commons_models.SoftDeleteTimeStampedModel):
    facility = models.ForeignKey("Facility", on_delete=models.CASCADE, null=False, blank=False)
    name = models.CharField(max_length=1000)
    num_rooms = models.IntegerField(validators=[MinValueValidator(0)], default=0)
    num_floors = models.IntegerField(validators=[MinValueValidator(0)], default=0)
    num_buildings = models.IntegerField(validators=[MinValueValidator(0)], default=0)  # For Internal Use only

    def __str__(self):
        return self.name + " under " + str(self.facility)


class Room(commons_models.SoftDeleteTimeStampedModel):
    building = models.ForeignKey("Building", on_delete=models.CASCADE, null=False, blank=False)
    num = models.CharField(max_length=1000)
    floor = models.IntegerField(validators=[MinValueValidator(0)], default=0)
    beds_capacity = models.IntegerField(validators=[MinValueValidator(0)], default=0)
    occupied_beds = models.IntegerField(validators=[MinValueValidator(0)], default=0)
    room_type = models.IntegerField(choices=commons_facility_constants.ROOM_TYPES)

    def __str__(self):
        return self.num + " under " + str(self.building)


class StaffRoomAllocation(commons_models.SoftDeleteTimeStampedModel):
    staff = models.ForeignKey(User, on_delete=models.CASCADE, null=False, blank=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, null=False, blank=False)

    def __str__(self):
        return str(self.staff) + " Allocated For " + str(self.room)


class InventoryItem(commons_models.SoftDeleteTimeStampedModel):
    name = models.CharField(max_length=1000)
    description = models.TextField()
    minimum_stock = models.IntegerField(validators=[MinValueValidator(0)], default=0)
    unit = models.CharField(max_length=20)

    def __str__(self):
        return self.name + " with unit " + self.unit + " with minimum stock " + str(self.minimum_stock)


class Inventory(commons_models.SoftDeleteTimeStampedModel):
    facility = models.ForeignKey("Facility", on_delete=models.CASCADE, null=False, blank=False)
    item = models.ForeignKey("InventoryItem", on_delete=models.CASCADE)
    quantitiy = models.IntegerField(validators=[MinValueValidator(0)], default=0)

    def __str__(self):
        return self.item.name + " : " + str(self.quantitiy) + " " + self.item.unit + " in " + str(self.facility)

    class Meta:
        verbose_name_plural = "Inventories"


class InventoryLog(commons_models.SoftDeleteTimeStampedModel):
    inventory = models.ForeignKey("Inventory", on_delete=models.CASCADE)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    prev_count = models.IntegerField(validators=[MinValueValidator(0)], default=0)
    new_count = models.IntegerField(validators=[MinValueValidator(0)], default=0)

    def __str__(self):
        return (
            "Item "
            + str(self.inventory)
            + " Updated from "
            + str(self.prev_count)
            + " to "
            + str(self.new_count)
            + " updated by "
            + str(self.updated_by)
        )


class FacilityUser(commons_models.SoftDeleteTimeStampedModel):
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_users")
