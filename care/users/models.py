from django.contrib.auth.models import AbstractUser, UserManager
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.urls import reverse

DISTRICT_CHOICES = [
    (1, "Thiruvananthapuram"),
    (2, "Kollam"),
    (3, "Pathanamthitta"),
    (4, "Alappuzha"),
    (5, "Kottayam"),
    (6, "Idukki"),
    (7, "Ernakulam"),
    (8, "Thrissur"),
    (9, "Palakkad"),
    (10, "Malappuram"),
    (11, "Kozhikode"),
    (12, "Wayanad"),
    (13, "Kannur"),
    (14, "Kasargode"),
]

GENDER_CHOICES = [(1, "Male"), (2, "Female"), (3, "Non-binary")]

phone_number_regex = RegexValidator(
    regex=r"^((\+91|91|0)[\- ]{0,1})?[456789]\d{9}$",
    message="Please Enter 10/11 digit mobile number or landline as 0<std code><phone number>",
    code="invalid_mobile",
)


class State(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.name}"


class District(models.Model):
    state = models.ForeignKey(State, on_delete=models.PROTECT)
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.name}"


LOCAL_BODY_CHOICES = (
    # Panchayath levels
    (1, "Grama Panchayath"),
    (2, "Block Panchayath"),
    (3, "District Panchayath"),
    # Municipality levels
    (10, "Municipality"),
    # Corporation levels
    (20, "Corporation"),
    # Unknown
    (50, "Others"),
)


class LocalBody(models.Model):
    district = models.ForeignKey(District, on_delete=models.PROTECT)

    name = models.CharField(max_length=255)
    body_type = models.IntegerField(choices=LOCAL_BODY_CHOICES)
    localbody_code = models.CharField(max_length=20, blank=True)

    class Meta:
        unique_together = (
            "district",
            "body_type",
            "name",
        )

    def __str__(self):
        return f"{self.name} ({self.body_type})"


class CustomUserManager(UserManager):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(deleted=False)

    def create_superuser(self, username, email, password, **extra_fields):
        district_id = extra_fields["district"]
        district = District.objects.get(id=district_id)
        extra_fields["district"] = district
        return super().create_superuser(username, email, password, **extra_fields)


class Skill(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        return self.name
