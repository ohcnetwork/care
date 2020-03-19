from django.db import models
from django.contrib.auth import get_user_model
from care.users.models import DISTRICT_CHOICES
from django.core.validators import MaxValueValidator, MinValueValidator


User = get_user_model()


class DateBaseModel(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class FacilityLocation(DateBaseModel):
    district = models.IntegerField(choices=DISTRICT_CHOICES, blank=False)

    def __str__(self):
        return self.district


class Facility(DateBaseModel):
    name = models.CharField(max_length=1000, blank=False, null=False)
    is_active = models.BooleanField(default=True)
    bed_capacity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    icu_capacity = models.IntegerField(default=0, validators=[MinValueValidator(0)])

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Facilities"


class FacilityStaff(DateBaseModel):
    facility = models.ForeignKey(
        "Facility", on_delete=models.CASCADE, null=False, blank=False
    )
    staff = models.ForeignKey(User, on_delete=models.CASCADE, null=False, blank=False)

    def __str__(self):
        return str(self.staff) + " for facility " + str(self.facility)


class FacilityVolunteer(DateBaseModel):
    facility = models.ForeignKey(
        "Facility", on_delete=models.CASCADE, null=False, blank=False
    )
    volunteer = models.ForeignKey(
        User, on_delete=models.CASCADE, null=False, blank=False
    )

    def __str__(self):
        return str(self.volunteer) + " for facility " + str(self.facility)
