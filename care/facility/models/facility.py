from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from multiselectfield import MultiSelectField
from multiselectfield.utils import get_max_length
from simple_history.models import HistoricalRecords

from care.facility.models import FacilityBaseModel, reverse_choices_class
from care.facility.models.mixins.permissions.facility import (
    FacilityPermissionMixin,
    FacilityRelatedPermissionMixin,
)
from care.users.models import District, LocalBody, State, Ward
from care.utils.models.validators import mobile_or_landline_number_validator

User = get_user_model()


# Facility Model Start
# BASE_ROOM_TYPES = [
#     (1, "General Bed"),
#     (10, "ICU"),
#     (20, "Ventilator"),
#     (30, "Covid Beds"),
#     (100, "Covid Ventilators"),
#     (110, "Covid ICU"),
#     (120, "Covid Oxygen beds"),
#     (150, "Oxygen beds"),
# ]
#
# ROOM_TYPES = [
#     (0, "Total"),
#     (2, "Hostel"),
#     (3, "Single Room with Attached Bathroom"),
#     (40, "KASP Beds"),
#     (50, "KASP ICU beds"),
#     (60, "KASP Oxygen beds"),
#     (70, "KASP Ventilator beds"),
# ]
#
# FEATURE_CHOICES = [
#     (1, "CT Scan Facility"),
#     (2, "Maternity Care"),
#     (3, "X-Ray facility"),
#     (4, "Neonatal care"),
#     (5, "Operation theater"),
#     (6, "Blood Bank"),
# ]
class BaseRoomTypes(models.IntegerChoices):
    GENERAL_BED = 1, _("General Bed")
    ICU = 10, _("ICU")
    VENTILATOR = 20, _("Ventilator")
    COVID_BEDS = 30, _("Covid Beds")
    COVID_VENTILATORS = 100, _("Covid Ventilators")
    COVID_ICU = 110, _("Covid ICU")
    COVID_OXYGEN_BEDS = 120, _("Covid Oxygen beds")
    OXYGEN_BEDS = 150, _("Oxygen beds")


class RoomTypes(BaseRoomTypes):
    TOTAL = 0, _("Total")
    HOSTEL = 2, _("Hostel")
    SINGLE_ROOM_WITH_ATTACHED_BATHROOM = 3, _("Single Room with Attached Bathroom")
    KASP_BEDS = 40, _("KASP Beds")
    KASP_ICU_BEDS = 50, _("KASP ICU beds")
    KASP_OXYGEN_BEDS = 60, _("KASP Oxygen beds")
    KASP_VENTILATOR_BEDS = 70, _("KASP Ventilator beds")


class FeatureChoices(models.IntegerChoices):
    CT_SCAN_FACILITY = 1, _("CT Scan Facility")
    MATERNITY_CARE = 2, _("Maternity Care")
    X_RAY_FACILITY = 3, _("X-Ray facility")
    NEONATAL_CARE = 4, _("Neonatal care")
    OPERATION_THEATER = 5, _("Operation theater")
    BLOOD_BANK = 6, _("Blood Bank")


REVERSE_ROOM_TYPES = reverse_choices_class(RoomTypes)


# FACILITY_TYPES = [
#     (1, "Educational Inst"),
#     (2, "Private Hospital"),
#     (3, "Other"),
#     (4, "Hostel"),
#     (5, "Hotel"),
#     (6, "Lodge"),
#     (7, "TeleMedicine"),
#     # (8, "Govt Hospital"), # Change from "Govt Hospital" to "Govt Medical College Hospitals"
#     (9, "Govt Labs"),
#     (10, "Private Labs"),
#     # Use 8xx for Govt owned hospitals and health centres
#     (800, "Primary Health Centres"),
#     # (801, "24x7 Public Health Centres"), # Change from "24x7 Public Health Centres" to "Primary Health Centres"
#     (802, "Family Health Centres"),
#     (803, "Community Health Centres"),
#     # (820, "Urban Primary Health Center"),   # Change from "Urban Primary Health Center" to "Primary Health Centres"
#     (830, "Taluk Hospitals"),
#     # (831, "Taluk Headquarters Hospitals"),     # Change from "Taluk Headquarters Hospitals" to "Taluk Hospitals"
#     (840, "Women and Child Health Centres"),
#     # (850, "General hospitals"),  # Change from "General hospitals" to "District Hospitals"
#     (860, "District Hospitals"),
#     (870, "Govt Medical College Hospitals"),
#     (900, "Co-operative hospitals"),
#     (910, "Autonomous healthcare facility"),
#     # Use 9xx for Labs
#     # (950, "Corona Testing Labs"),    # Change from "Corona Testing Labs" to "Govt Labs"
#     # Use 10xx for Corona Care Center
#     # (1000, "Corona Care Centre"),   # Change from "Corona Care Centre" to "Other"
#     (1010, "COVID-19 Domiciliary Care Center"),
#     # Use 11xx for First Line Treatment Centre
#     (1100, "First Line Treatment Centre"),
#     # Use 12xx for Second Line Treatment Center
#     (1200, "Second Line Treatment Center"),
#     # Use 13xx for Shifting Centers
#     (1300, "Shifting Centre"),
#     # Use 14xx for Covid Management Centers.
#     (1400, "Covid Management Center"),
#     # Use 15xx for Resource Management Centers.
#     (1500, "Request Approving Center"),
#     (1510, "Request Fulfilment Center"),
#     # Use 16xx for War Rooms.
#     (1600, "District War Room"),
# ]

class FacilityTypes(models.IntegerChoices):
    EDUCATIONAL_INST = 1, _("Educational Inst")
    PRIVATE_HOSPITAL = 2, _("Private Hospital")
    OTHER = 3, _("Other")
    HOSTEL = 4, _("Hostel")
    HOTEL = 5, _("Hotel")
    LODGE = 6, _("Lodge")
    TELEMEDICINE = 7, _("TeleMedicine")
    # (8, "Govt Hospital"), # Change from "Govt Hospital" to "Govt Medical College Hospitals"
    GOVT_LABS = 9, _("Govt Labs")
    PRIVATE_LABS = 10, _("Private Labs")
    #     # Use 8xx for Govt owned hospitals and health centres
    PRIMARY_HEALTH_CENTRES = 800, _("Primary Health Centres")
    # (801, "24x7 Public Health Centres"), # Change from "24x7 Public Health Centres" to "Primary Health Centres"
    FAMILY_HEALTH_CENTRES = 802, _("Family Health Centres")
    COMMUNITY_HEALTH_CENTRES = 803, _("Community Health Centres")
    # (820, "Urban Primary Health Center"),   # Change from "Urban Primary Health Center" to "Primary Health Centres"
    TALUK_HOSPITALS = 830, _("Taluk Hospitals")
    # (831, "Taluk Headquarters Hospitals"),     # Change from "Taluk Headquarters Hospitals" to "Taluk Hospitals"
    WOMEN_AND_CHILD_HEALTH_CENTRES = 840, _("Women and Child Health Centres")
    # (850, "General hospitals"),  # Change from "General hospitals" to "District Hospitals"
    DISTRICT_HOSPITALS = 860, _("District Hospitals")
    GOVT_MEDICAL_COLLEGE_HOSPITALS = 870, _("Govt Medical College Hospitals")
    COOPERATIVE_HOSPITALS = 900, _("Co-operative hospitals")
    AUTONOMOUS_HEALTHCARE_FACILITY = 910, _("Autonomous healthcare facility")
    # Use 9xx for Labs
    # (950, "Corona Testing Labs"),    # Change from "Corona Testing Labs" to "Govt Labs"
    # Use 10xx for Corona Care Center
    # (1000, "Corona Care Centre"),   # Change from "Corona Care Centre" to "Other"
    COVID19_DOMICILIARY_CARE_CENTER = 1010, _("COVID-19 Domiciliary Care Center")
    # Use 11xx for First Line Treatment Centre
    FIRST_LINE_TREATMENT_CENTRE = 1100, _("First Line Treatment Centre")
    # Use 12xx for Second Line Treatment Center
    SECOND_LINE_TREATMENT_CENTER = 1200, _("Second Line Treatment Center")
    # Use 13xx for Shifting Centers
    SHIFTING_CENTER = 1300, _("Shifting Centre")
    # Use 14xx for Covid Management Centers.
    COVID_MANAGEMENT_CENTER = 1400, _("Covid Management Center")
    # Use 15xx for Resource Management Centers.
    REQUEST_APPROVING_CENTER = 1500, _("Request Approving Center")
    REQUEST_FULFILMENT_CENTER = 1510, _("Request Fulfilment Center")
    # Use 16xx for War Rooms.
    DISTRICT_WAR_ROOM = 1600, _("District War Room")


REVERSE_FACILITY_TYPES = reverse_choices_class(FacilityTypes)


# DOCTOR_TYPES = [
#     (1, "General Medicine"),
#     (2, "Pulmonology"),
#     (3, "Critical Care"),
#     (4, "Paediatrics"),
#     (5, "Other Speciality"),
# ]
class DoctorTypes(models.IntegerChoices):
    GENERAL_MEDICINE = 1, _("General Medicine")
    PULMONOLOGY = 2, _("Pulmonology")
    CRITICAL_CARE = 3, _("Critical Care")
    PAEDIATRICS = 4, _("Paediatrics")
    OTHER_SPECIALITY = 5, _("Other Speciality")


REVERSE_DOCTOR_TYPES = reverse_choices_class(DoctorTypes)

REVERSE_FEATURE_CHOICES = reverse_choices_class(FeatureChoices)


class Facility(FacilityBaseModel, FacilityPermissionMixin):
    name = models.CharField(max_length=1000, blank=False, null=False)
    is_active = models.BooleanField(default=True)
    verified = models.BooleanField(default=False)
    facility_type = models.IntegerField(choices=FacilityTypes.choices)
    kasp_empanelled = models.BooleanField(default=False, blank=False, null=False)
    features = MultiSelectField(
        choices=FeatureChoices.choices,
        null=True,
        blank=True,
        max_length=get_max_length(FeatureChoices.choices, None),
    )

    longitude = models.DecimalField(
        max_digits=22, decimal_places=16, null=True, blank=True
    )
    latitude = models.DecimalField(
        max_digits=22, decimal_places=16, null=True, blank=True
    )
    pincode = models.IntegerField(default=None, null=True)
    address = models.TextField()
    ward = models.ForeignKey(Ward, on_delete=models.SET_NULL, null=True, blank=True)
    local_body = models.ForeignKey(
        LocalBody, on_delete=models.SET_NULL, null=True, blank=True
    )
    district = models.ForeignKey(
        District, on_delete=models.SET_NULL, null=True, blank=True
    )
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True)

    oxygen_capacity = models.IntegerField(default=0)
    type_b_cylinders = models.IntegerField(default=0)
    type_c_cylinders = models.IntegerField(default=0)
    type_d_cylinders = models.IntegerField(default=0)

    expected_oxygen_requirement = models.IntegerField(default=0)
    expected_type_b_cylinders = models.IntegerField(default=0)
    expected_type_c_cylinders = models.IntegerField(default=0)
    expected_type_d_cylinders = models.IntegerField(default=0)

    phone_number = models.CharField(
        max_length=14, blank=True, validators=[mobile_or_landline_number_validator]
    )
    corona_testing = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )

    users = models.ManyToManyField(
        User,
        through="FacilityUser",
        related_name="facilities",
        through_fields=("facility", "user"),
    )

    cover_image_url = models.CharField(
        blank=True, null=True, default=None, max_length=500
    )
    middleware_address = models.CharField(null=True, default=None, max_length=200)

    class Meta:
        verbose_name_plural = "Facilities"

    def read_cover_image_url(self):
        if self.cover_image_url:
            return f"{settings.FACILITY_S3_BUCKET_EXTERNAL_ENDPOINT}/{settings.FACILITY_S3_BUCKET}/{self.cover_image_url}"
        return None

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

    CSV_MAPPING = {
        "name": "Facility Name",
        "facility_type": "Facility Type",
        "address": "Address",
        "ward__name": "Ward Name",
        "ward__number": "Ward Number",
        "local_body__name": "Local Body",
        "district__name": "District",
        "state__name": "State",
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

    facility = models.OneToOneField(
        Facility, unique=True, null=True, blank=True, on_delete=models.SET_NULL
    )
    local_body = models.ForeignKey(
        LocalBody, null=True, blank=True, on_delete=models.SET_NULL
    )
    district = models.ForeignKey(
        District, null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="cons_facilitylocalgovtbody_only_one_null",
                check=models.Q(local_body__isnull=False)
                      | models.Q(district__isnull=False),
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
    facility = models.ForeignKey(
        "Facility", on_delete=models.CASCADE, null=False, blank=False
    )
    area = models.IntegerField(choices=DoctorTypes.choices)
    count = models.PositiveIntegerField()

    def __str__(self):
        return str(self.facility) + str(self.count)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["facility", "area"],
                condition=models.Q(deleted=False),
                name="unique_facility_doctor",
            )
        ]

    CSV_RELATED_MAPPING = {
        "hospitaldoctors__area": "Doctors Area",
        "hospitaldoctors__count": "Doctors Count",
    }

    CSV_MAKE_PRETTY = {"hospitaldoctors__area": (lambda x: REVERSE_DOCTOR_TYPES[x])}


class FacilityCapacity(FacilityBaseModel, FacilityRelatedPermissionMixin):
    facility = models.ForeignKey(
        "Facility", on_delete=models.CASCADE, null=False, blank=False
    )
    room_type = models.IntegerField(choices=RoomTypes.choices)
    total_capacity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    current_capacity = models.IntegerField(default=0, validators=[MinValueValidator(0)])

    history = HistoricalRecords()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["facility", "room_type"],
                condition=models.Q(deleted=False),
                name="unique_facility_room_type",
            )
        ]
        verbose_name_plural = "Facility Capacities"

    CSV_RELATED_MAPPING = {
        "facilitycapacity__room_type": "Room Type",
        "facilitycapacity__total_capacity": "Total Capacity",
        "facilitycapacity__current_capacity": "Current Capacity",
        "facilitycapacity__modified_date": "Updated Date",
        "oxygen_capacity": "Oxygen Capacity",
        "type_b_cylinders": "B Type Oxygen Cylinder",
        "type_c_cylinders": "C Type Oxygen Cylinder",
        "type_d_cylinders": "Jumbo D Type Oxygen Cylinder",
    }

    CSV_MAKE_PRETTY = {
        "facilitycapacity__room_type": (lambda x: REVERSE_ROOM_TYPES[x]),
        "facilitycapacity__modified_date": (lambda x: x.strftime("%d-%m-%Y")),
    }

    def __str__(self):
        return (
            str(self.facility)
            + " "
            + REVERSE_ROOM_TYPES[self.room_type]
            + " "
            + str(self.total_capacity)
        )


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
    num_buildings = models.IntegerField(
        validators=[MinValueValidator(0)], default=0
    )  # For Internal Use only

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
    room_type = models.IntegerField(choices=RoomTypes.choices)

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


class FacilityUser(models.Model):
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="created_users"
    )

    class Meta:
        unique_together = (
            "facility",
            "user",
        )

    def __str__(self):
        return str(self.user) + " under " + str(self.facility)

    CSV_MAPPING = {
        "facility__name": "Facility Name",
        "user__username": "User Username",
        "created_by__username": "Created By Username",
    }
    CSV_MAKE_PRETTY = {}
