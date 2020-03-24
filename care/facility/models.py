from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.core.validators import RegexValidator
from django.db import models
from location_field.models.spatial import LocationField

User = get_user_model()


class FacilityBaseModel(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def delete(self):
        self.deleted = True
        self.save()


# Facility Model Start

ROOM_TYPES = [(0, "Total"), (1, "Normal"), (2, "Hostel"), (10, "ICU"), (20, "Ventilator")]

FACILITY_TYPES = [(1, "Educational Inst"), (2, "Hospital"), (3, "Other")]

DOCTOR_TYPES = [
    (1, "General Medicine"),
    (2, "Pulmonology"),
    (3, "Critical Care"),
    (4, "Paediatrics"),
    (5, "Other Speciality"),
]

phone_number_regex = RegexValidator(
    regex="^((\+91|91|0)[\- ]{0,1})?[456789]\d{9}$",
    message="Please Enter 10/11 digit mobile number or landline as 0<std code><phone number>",
    code="invalid_mobile",
)


class Facility(FacilityBaseModel):
    name = models.CharField(max_length=1000, blank=False, null=False)
    is_active = models.BooleanField(default=True)
    verified = models.BooleanField(default=False)
    district = models.IntegerField(choices=User.DISTRICT_CHOICES, blank=False)
    facility_type = models.IntegerField(choices=FACILITY_TYPES)
    address = models.TextField()
    location = LocationField(based_fields=["address"], zoom=7, blank=True, null=True)
    oxygen_capacity = models.IntegerField(default=0)
    phone_number = models.CharField(max_length=14, blank=True, validators=[phone_number_regex])
    corona_testing = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Facilities"


class HospitalDoctors(FacilityBaseModel):
    facility = models.ForeignKey(
        "Facility", on_delete=models.CASCADE, null=False, blank=False
    )
    area = models.IntegerField(choices=DOCTOR_TYPES)
    count = models.IntegerField()

    def __str__(self):
        return str(self.facility) + str(self.count)

    class Meta:
        unique_together = ["facility", "area", "deleted"]


class FacilityCapacity(FacilityBaseModel):
    facility = models.ForeignKey(
        "Facility", on_delete=models.CASCADE, null=False, blank=False
    )
    room_type = models.IntegerField(choices=ROOM_TYPES)
    total_capacity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    current_capacity = models.IntegerField(default=0, validators=[MinValueValidator(0)])

    class Meta:
        unique_together = ["facility", "room_type", "deleted"]


class FacilityStaff(FacilityBaseModel):
    facility = models.ForeignKey(
        "Facility", on_delete=models.CASCADE, null=False, blank=False
    )
    staff = models.ForeignKey(User, on_delete=models.CASCADE, null=False, blank=False)

    def __str__(self):
        return str(self.staff) + " for facility " + str(self.facility)


class FacilityVolunteer(FacilityBaseModel):
    facility = models.ForeignKey(
        "Facility", on_delete=models.CASCADE, null=False, blank=False
    )
    volunteer = models.ForeignKey(
        User, on_delete=models.CASCADE, null=False, blank=False
    )

    def __str__(self):
        return str(self.volunteer) + " for facility " + str(self.facility)


# Facility Model End


# Building Model Start


class Building(FacilityBaseModel):
    facility = models.ForeignKey(
        "Facility", on_delete=models.CASCADE, null=False, blank=False
    )
    name = models.CharField(max_length=1000)
    num_rooms = models.IntegerField(validators=[MinValueValidator(0)], default=0)
    num_floors = models.IntegerField(validators=[MinValueValidator(0)], default=0)

    def __str__(self):
        return self.name + " under " + str(self.facility)


# Building Model End


# Room Model Start


class Room(FacilityBaseModel):
    building = models.ForeignKey(
        "Building", on_delete=models.CASCADE, null=False, blank=False
    )
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
        return (
            self.name
            + " with unit "
            + self.unit
            + " with minimum stock "
            + str(self.minimum_stock)
        )


class Inventory(FacilityBaseModel):
    facility = models.ForeignKey(
        "Facility", on_delete=models.CASCADE, null=False, blank=False
    )
    item = models.ForeignKey("InventoryItem", on_delete=models.CASCADE)
    quantitiy = models.IntegerField(validators=[MinValueValidator(0)], default=0)

    def __str__(self):
        return (
            self.item.name
            + " : "
            + str(self.quantitiy)
            + " "
            + self.item.unit
            + " in "
            + str(self.facility)
        )

    class Meta:
        verbose_name_plural = "Inventories"


class InventoryLog(FacilityBaseModel):
    inventory = models.ForeignKey("Inventory", on_delete=models.CASCADE)
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
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


class Ambulance(FacilityBaseModel):
    vehicle_number_regex = RegexValidator(
        regex="^[A-Z]{2}[0-9]{1,2}[A-Z]{1,2}[0-9]{1,4}$",
        message="Please Enter the vehicle number in all uppercase without spaces, eg: KL13AB1234",
        code="invalid_vehicle_number",
    )
    INSURANCE_YEAR_CHOICES = ((2020, 2020), (2021, 2021), (2022, 2022))

    vehicle_number = models.CharField(max_length=20, validators=[vehicle_number_regex], unique=True, db_index=True)

    owner_name = models.CharField(max_length=255)
    owner_phone_number = models.CharField(max_length=14, validators=[phone_number_regex])
    owner_is_smart_phone = models.BooleanField(default=True)

    primary_district = models.IntegerField(choices=User.DISTRICT_CHOICES, blank=False)
    secondary_district = models.IntegerField(choices=User.DISTRICT_CHOICES, blank=True, null=True)
    third_district = models.IntegerField(choices=User.DISTRICT_CHOICES, blank=True, null=True)

    has_oxygen = models.BooleanField()
    has_ventilator = models.BooleanField()
    has_suction_machine = models.BooleanField()
    has_defibrillator = models.BooleanField()

    insurance_valid_till_year = models.IntegerField(choices=INSURANCE_YEAR_CHOICES)

    @property
    def drivers(self):
        return self.ambulancedriver_set.filter(deleted=False)

    def __str__(self):
        return f"Ambulance - {self.owner_name}({self.owner_phone_number})"


class AmbulanceDriver(FacilityBaseModel):
    ambulance = models.ForeignKey(Ambulance, on_delete=models.CASCADE)

    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=14, validators=[phone_number_regex])
    is_smart_phone = models.BooleanField()

    def __str__(self):
        return f"Driver: {self.name}({self.phone_number})"
