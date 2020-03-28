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
        return f"State: {self.name}"


class District(models.Model):
    state = models.ForeignKey(State, on_delete=models.PROTECT)
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"District: {self.name} - {self.state.name}"


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
        return f"LocalBody: {self.name} ({self.body_type}) / {self.district}"


class CustomUserManager(UserManager):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(deleted=False)


class Skill(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        return self.name


class User(AbstractUser):
    TYPE_VALUE_MAP = {
        "Doctor": 5,
        "Staff": 10,
        "Patient": 15,
        "Volunteer": 20,
    }
    TYPE_CHOICES = [(value, name) for name, value in TYPE_VALUE_MAP.items()]

    user_type = models.IntegerField(choices=TYPE_CHOICES, blank=False)
    district = models.IntegerField(choices=DISTRICT_CHOICES, blank=False)
    new_district = models.ForeignKey(District, on_delete=models.PROTECT, null=True)
    phone_number = models.CharField(max_length=14, validators=[phone_number_regex])
    gender = models.IntegerField(choices=GENDER_CHOICES, blank=False)
    age = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(100)])
    skill = models.ForeignKey("Skill", on_delete=models.SET_NULL, null=True, blank=True)
    verified = models.BooleanField(default=False)
    deleted = models.BooleanField(default=False)
    REQUIRED_FIELDS = [
        "user_type",
        "email",
        "phone_number",
        "age",
        "gender",
        "district",
    ]

    objects = CustomUserManager()

    def delete(self, *args, **kwargs):
        self.deleted = True
        self.save()

    def get_absolute_url(self):
        return reverse("users:detail", kwargs={"username": self.username})
