from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models
from location_field.models.spatial import LocationField
from partial_index import PQ, PartialIndex
from simple_history.models import HistoricalRecords

from care.facility.models import FacilityBaseModel, phone_number_regex, reverse_choices
from care.facility.models.mixins.permissions.facility import FacilityPermissionMixin, FacilityRelatedPermissionMixin
from care.users.models import District, LocalBody, State


User = get_user_model()

# Facility Model Start

ROOM_TYPES = [
    (0, "Total"),
    (1, "General Bed"),
    (2, "Hostel"),
    (3, "Single Room with Attached Bathroom"),
    (10, "ICU"),
    (20, "Ventilator"),
]

REVERSE_ROOM_TYPES = reverse_choices(ROOM_TYPES)

FACILITY_TYPES = [
    (1, "Educational Inst"),
    (2, "Private Hospital"),
    (3, "Other"),
    (4, "Hostel"),
    (5, "Hotel"),
    (6, "Lodge"),
    (7, "TeleMedicine"),
    (8, "Govt Hospital"),
    (9, "Labs"),
    # Use 8xx for Govt owned hospitals and health centres
    (800, "Primary Health Centres"),
    (801, "24x7 Public Health Centres"),
    (802, "Family Health Centres"),
    (803, "Community Health Centres"),
    (820, "Urban Primary Health Center"),
    (830, "Taluk Hospitals"),
    (831, "Taluk Headquarters Hospitals"),
    (840, "Women and Child Health Centres"),
    (850, "General hospitals"),  # TODO: same as 8, need to merge
    (860, "District Hospitals"),
    (870, "Govt Medical College Hospitals"),
    # Use 9xx for Labs
    (950, "Corona Testing Labs"),
    # Use 10xx for Corona Care Center
    (1000, "Corona Care Centre"),
    # Use 11xx for First Line Treatment Centre
    (1100, "First Line Treatment Centre"),
]

REVERSE_FACILITY_TYPES = reverse_choices(FACILITY_TYPES)

DOCTOR_TYPES = [
    (1, "General Medicine"),
    (2, "Pulmonology"),
    (3, "Critical Care"),
    (4, "Paediatrics"),
    (5, "Other Speciality"),
]

REVERSE_DOCTOR_TYPES = reverse_choices(DOCTOR_TYPES)


class Facility(FacilityBaseModel, FacilityPermissionMixin):
    name = models.CharField(max_length=1000, blank=False, null=False)
    is_active = models.BooleanField(default=True)
    verified = models.BooleanField(default=False)
    facility_type = models.IntegerField(choices=FACILITY_TYPES)

    location = LocationField(based_fields=["address"], zoom=7, blank=True, null=True)
    pincode = models.IntegerField(default=None, null=True)
    address = models.TextField()
    local_body = models.ForeignKey(LocalBody, on_delete=models.SET_NULL, null=True, blank=True)
    district = models.ForeignKey(District, on_delete=models.SET_NULL, null=True, blank=True)
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True)

    oxygen_capacity = models.IntegerField(default=0)
    phone_number = models.CharField(max_length=14, blank=True, validators=[phone_number_regex])
    corona_testing = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    users = models.ManyToManyField(
        User, through="FacilityUser", related_name="facilities", through_fields=("facility", "user"),
    )

    class Meta:
        verbose_name_plural = "Facilities"

    def __str__(self):
        return f"{self.name}"

    def has_object_destroy_permission(self, request):
        return request.user.is_superuser

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

    CSV_MAPPING = {
        "name": "Facility Name",
        "facility_type": "Facility Type",
        "address": "Address",
        "local_body__name": "Local Body",
        "district__name": "District",
        "state__name": "State",
        "oxygen_capacity": "Oxygen Capacity",
        "phone_number": "Phone Number",
    }

    CSV_MAKE_PRETTY = {"facility_type": (lambda x: REVERSE_FACILITY_TYPES[x])}


class FacilityLocalGovtBody(models.Model):
    """
    DEPRECATED_FROM: 2020-03-29
    DO NOT USE

    Model to relate a Facility to a local self governing body
    In ideal cases, the facility will be related to a local governing body.
    But in other cases, and in cases of incomplete data, we will only have information till a district level
    """

    facility = models.OneToOneField(Facility, unique=True, null=True, blank=True, on_delete=models.SET_NULL)
    local_body = models.ForeignKey(LocalBody, null=True, blank=True, on_delete=models.SET_NULL)
    district = models.ForeignKey(District, null=True, blank=True, on_delete=models.SET_NULL)

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


class HospitalDoctors(FacilityBaseModel, FacilityRelatedPermissionMixin):
    facility = models.ForeignKey("Facility", on_delete=models.CASCADE, null=False, blank=False)
    area = models.IntegerField(choices=DOCTOR_TYPES)
    count = models.IntegerField()

    def __str__(self):
        return str(self.facility) + str(self.count)

    class Meta:
        indexes = [PartialIndex(fields=["facility", "area"], unique=True, where=PQ(deleted=False))]

    CSV_RELATED_MAPPING = {
        "hospitaldoctors__area": "Doctors Area",
        "hospitaldoctors__count": "Doctors Count",
    }

    CSV_MAKE_PRETTY = {"hospitaldoctors__area": (lambda x: REVERSE_DOCTOR_TYPES[x])}


class FacilityCapacity(FacilityBaseModel, FacilityRelatedPermissionMixin):
    facility = models.ForeignKey("Facility", on_delete=models.CASCADE, null=False, blank=False)
    room_type = models.IntegerField(choices=ROOM_TYPES)
    total_capacity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    current_capacity = models.IntegerField(default=0, validators=[MinValueValidator(0)])

    history = HistoricalRecords()

    class Meta:
        indexes = [PartialIndex(fields=["facility", "room_type"], unique=True, where=PQ(deleted=False))]

    CSV_RELATED_MAPPING = {
        "facilitycapacity__room_type": "Room Type",
        "facilitycapacity__total_capacity": "Total Capacity",
        "facilitycapacity__current_capacity": "Current Capacity",
        "facilitycapacity__modified_date": "Updated Date",
    }

    CSV_MAKE_PRETTY = {"facilitycapacity__room_type": (lambda x: REVERSE_ROOM_TYPES[x])}


class FacilityStaff(FacilityBaseModel):
    facility = models.ForeignKey("Facility", on_delete=models.CASCADE, null=False, blank=False)
    staff = models.ForeignKey(User, on_delete=models.CASCADE, null=False, blank=False)

    def __str__(self):
        return str(self.staff) + " for facility " + str(self.facility)


class FacilityVolunteer(FacilityBaseModel):
    facility = models.ForeignKey("Facility", on_delete=models.CASCADE, null=False, blank=False)
    volunteer = models.ForeignKey(User, on_delete=models.CASCADE, null=False, blank=False)

    def __str__(self):
        return str(self.volunteer) + " for facility " + str(self.facility)


# Facility Model End


# Building Model Start


class Building(FacilityBaseModel):
    facility = models.ForeignKey("Facility", on_delete=models.CASCADE, null=False, blank=False)
    name = models.CharField(max_length=1000)
    num_rooms = models.IntegerField(validators=[MinValueValidator(0)], default=0)
    num_floors = models.IntegerField(validators=[MinValueValidator(0)], default=0)
    num_buildings = models.IntegerField(validators=[MinValueValidator(0)], default=0)  # For Internal Use only

    def __str__(self):
        return self.name + " under " + str(self.facility)


# Building Model End


# Room Model Start


class Room(FacilityBaseModel):
    building = models.ForeignKey("Building", on_delete=models.CASCADE, null=False, blank=False)
    num = models.CharField(max_length=1000)
    floor = models.IntegerField(validators=[MinValueValidator(0)], default=0)
    beds_capacity = models.IntegerField(validators=[MinValueValidator(0)], default=0)
    occupied_beds = models.IntegerField(validators=[MinValueValidator(0)], default=0)
    room_type = models.IntegerField(choices=ROOM_TYPES)

    def __str__(self):
        return self.num + " under " + str(self.building)


class StaffRoomAllocation(FacilityBaseModel):
    staff = models.ForeignKey(User, on_delete=models.CASCADE, null=False, blank=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, null=False, blank=False)

    def __str__(self):
        return str(self.staff) + " Allocated For " + str(self.room)


# Room Model End

# Inventory Model Start


class InventoryItem(FacilityBaseModel):
    name = models.CharField(max_length=1000)
    description = models.TextField()
    minimum_stock = models.IntegerField(validators=[MinValueValidator(0)], default=0)
    unit = models.CharField(max_length=20)

    def __str__(self):
        return self.name + " with unit " + self.unit + " with minimum stock " + str(self.minimum_stock)


class Inventory(FacilityBaseModel):
    facility = models.ForeignKey("Facility", on_delete=models.CASCADE, null=False, blank=False)
    item = models.ForeignKey("InventoryItem", on_delete=models.CASCADE)
    quantitiy = models.IntegerField(validators=[MinValueValidator(0)], default=0)

    def __str__(self):
        return self.item.name + " : " + str(self.quantitiy) + " " + self.item.unit + " in " + str(self.facility)

    class Meta:
        verbose_name_plural = "Inventories"


class InventoryLog(FacilityBaseModel):
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


# Inventory Model End


class FacilityUser(models.Model):
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_users")

    class Meta:
        unique_together = (
            "facility",
            "user",
        )
