from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from care.facility.models.base import FacilityBaseModel
from care.users.models import District
from care.utils.models.validators import mobile_or_landline_number_validator

User = get_user_model()


# AMBULANCE_TYPES = [(1, "Basic"), (2, "Cardiac"), (3, "Hearse")]


class Ambulance(FacilityBaseModel):
    class AmbulanceTypeChoices(models.IntegerChoices):
        BASIC = 1, _("Basic")
        CARDIAC = 2, _("Cardiac")
        HEARSE = 3, _("Hearse")

    class InsuranceYearChoices(models.IntegerChoices):
        YEAR_2020 = 2020, _("2020")
        YEAR_2021 = 2021, _("2021")
        YEAR_2022 = 2022, _("2022")

    # INSURANCE_YEAR_CHOICES = ((2020, 2020), (2021, 2021), (2022, 2022))

    vehicle_number_regex = RegexValidator(
        regex="^[A-Z]{2}[0-9]{1,2}[A-Z]{0,2}[0-9]{1,4}$",
        message="Please Enter the vehicle number in all uppercase without spaces, eg: KL13AB1234",
        code="invalid_vehicle_number",
    )

    vehicle_number = models.CharField(
        max_length=20,
        validators=[vehicle_number_regex],
        unique=True,
        db_index=True,
    )

    owner_name = models.CharField(max_length=255)
    owner_phone_number = models.CharField(
        max_length=14, validators=[mobile_or_landline_number_validator]
    )
    owner_is_smart_phone = models.BooleanField(default=True)

    # primary_district = models.IntegerField(choices=DISTRICT_CHOICES, blank=False)
    # secondary_district = models.IntegerField(choices=DISTRICT_CHOICES, blank=True, null=True)
    # third_district = models.IntegerField(choices=DISTRICT_CHOICES, blank=True, null=True)

    primary_district = models.ForeignKey(
        District,
        on_delete=models.PROTECT,
        null=True,
        related_name="primary_ambulances",
    )
    secondary_district = models.ForeignKey(
        District,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="secondary_ambulances",
    )
    third_district = models.ForeignKey(
        District,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="third_ambulances",
    )

    has_oxygen = models.BooleanField()
    has_ventilator = models.BooleanField()
    has_suction_machine = models.BooleanField()
    has_defibrillator = models.BooleanField()

    insurance_valid_till_year = models.IntegerField(choices=InsuranceYearChoices.choices)

    ambulance_type = models.IntegerField(
        choices=AmbulanceTypeChoices.choices, blank=False, default=AmbulanceTypeChoices.BASIC
    )

    price_per_km = models.DecimalField(max_digits=7, decimal_places=2, null=True)
    has_free_service = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )

    @property
    def drivers(self):
        return self.ambulancedriver_set.filter(deleted=False)

    def __str__(self):
        return f"Ambulance - {self.owner_name}({self.owner_phone_number})"

    @staticmethod
    def has_read_permission(request):
        return True

    def has_object_read_permission(self, request):
        return (
            request.user.is_superuser
            or request.user == self.created_by
            or (
                request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]
                and request.user.district
                in [
                    self.primary_district,
                    self.secondary_district,
                    self.third_district,
                ]
            )
        )

    @staticmethod
    def has_write_permission(request):
        return True

    def has_object_write_permission(self, request):
        return request.user.is_superuser

    def has_object_update_permission(self, request):
        return (
            request.user.is_superuser
            or request.user == self.created_by
            or (
                request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]
                and request.user.district
                in [
                    self.primary_district,
                    self.secondary_district,
                    self.third_district,
                ]
            )
        )

    # class Meta:
    #     constraints = [
    #         models.CheckConstraint(
    #             name="ambulance_free_or_price",
    #             check=models.Q(price_per_km__isnull=False)
    #             | models.Q(has_free_service=True),
    #         )
    #     ]


class AmbulanceDriver(FacilityBaseModel):
    ambulance = models.ForeignKey(Ambulance, on_delete=models.CASCADE)

    name = models.CharField(max_length=255)
    phone_number = models.CharField(
        max_length=14, validators=[mobile_or_landline_number_validator]
    )
    is_smart_phone = models.BooleanField()

    def __str__(self):
        return f"Driver: {self.name} ({self.phone_number})"
