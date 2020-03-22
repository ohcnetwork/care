from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.urls import reverse
from django.core.validators import RegexValidator
from django.core.validators import MaxValueValidator, MinValueValidator


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
    TYPE_CHOICES = [(5, "Doctor"), (10, "Staff"), (15, "Patient"), (20, "Volunteer")]

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
        (14, "Kasaragod"),
    ]

    GENDER_CHOICES = [(1, "Male"), (2, "Female"), (3, "Other")]

    user_type = models.IntegerField(choices=TYPE_CHOICES, blank=False)
    district = models.IntegerField(choices=DISTRICT_CHOICES, blank=False)
    phone_number_regex = RegexValidator(
        regex="^((\+91|91|0)[\- ]{0,1})?[456789]\d{9}$",
        message="Please Enter 10/11 digit mobile number or landline as 0<std code><phone number>",
        code="invalid_mobile",
    )
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

    def delete(self):
        self.deleted = True
        self.save()

    def get_absolute_url(self):
        return reverse("users:detail", kwargs={"username": self.username})
