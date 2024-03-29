import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from care.utils.models.base import BaseModel
from care.utils.models.validators import (
    UsernameValidator,
    mobile_or_landline_number_validator,
    mobile_validator,
)


def reverse_choices(choices):
    output = {}
    for choice in choices:
        output[choice[0]] = choice[1]
    return output


GENDER_CHOICES = [(1, "Male"), (2, "Female"), (3, "Non-binary")]
REVERSE_GENDER_CHOICES = reverse_choices(GENDER_CHOICES)

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
    (4, "Nagar Panchayath"),
    # Municipality levels
    (10, "Municipality"),
    # Corporation levels
    (20, "Corporation"),
    # Unknown
    (50, "Others"),
)


def reverse_lower_choices(choices):
    output = {}
    for choice in choices:
        output[choice[1].lower()] = choice[0]
    return output


REVERSE_LOCAL_BODY_CHOICES = reverse_lower_choices(LOCAL_BODY_CHOICES)


class LocalBody(models.Model):
    district = models.ForeignKey(District, on_delete=models.PROTECT)

    name = models.CharField(max_length=255)
    body_type = models.IntegerField(choices=LOCAL_BODY_CHOICES)
    localbody_code = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        unique_together = (
            "district",
            "body_type",
            "name",
        )
        verbose_name = "Local Body"
        verbose_name_plural = "Local Bodies"

    def __str__(self):
        return f"{self.name} ({self.body_type})"


class Ward(models.Model):
    local_body = models.ForeignKey(LocalBody, on_delete=models.PROTECT)
    name = models.CharField(max_length=255)
    number = models.IntegerField()

    class Meta:
        unique_together = (
            "local_body",
            "name",
            "number",
        )

    def __str__(self):
        return f"{self.name}"


class CustomUserManager(UserManager):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(deleted=False, is_active=True).select_related(
            "local_body", "district", "state"
        )

    def get_entire_queryset(self):
        return super().get_queryset().select_related("local_body", "district", "state")

    def create_superuser(self, username, email, password, **extra_fields):
        district = District.objects.all().first()
        data_command = (
            "load_data" if settings.IS_PRODUCTION is True else "load_dummy_data"
        )
        if not district:
            proceed = input(
                f"It looks like you haven't loaded district data. It is recommended to populate district data before you create a super user. Please run `python manage.py {data_command}`.\n Proceed anyway? [y/N]"
            )
            if proceed.lower() != "y":
                raise Exception("Aborted Superuser Creation")
            district = None

        extra_fields["district"] = district
        extra_fields["phone_number"] = "+919696969696"
        extra_fields["gender"] = 3
        extra_fields["user_type"] = 40
        return super().create_superuser(username, email, password, **extra_fields)


class Skill(BaseModel):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(null=True, blank=True, default="")

    def __str__(self):
        return self.name


class UserSkill(BaseModel):
    user = models.ForeignKey("User", on_delete=models.CASCADE, null=True, blank=True)
    skill = models.ForeignKey("Skill", on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["skill", "user"],
                condition=models.Q(deleted=False),
                name="unique_user_skill",
            )
        ]


class User(AbstractUser):
    external_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    username_validator = UsernameValidator()
    username = models.CharField(
        _("username"),
        max_length=150,
        unique=True,
        help_text=username_validator.message,
        validators=[username_validator],
        error_messages={"unique": _("A user with that username already exists.")},
    )

    TYPE_VALUE_MAP = {
        "Transportation": 2,
        "Pharmacist": 3,
        "Volunteer": 5,
        "StaffReadOnly": 9,
        "Staff": 10,
        "NurseReadOnly": 13,
        "Nurse": 14,
        "Doctor": 15,
        "Reserved": 20,
        "WardAdmin": 21,
        "LocalBodyAdmin": 23,
        "DistrictLabAdmin": 25,
        "DistrictReadOnlyAdmin": 29,
        "DistrictAdmin": 30,
        "StateLabAdmin": 35,
        "StateReadOnlyAdmin": 39,
        "StateAdmin": 40,
    }

    READ_ONLY_TYPES = (
        TYPE_VALUE_MAP["StaffReadOnly"],
        TYPE_VALUE_MAP["NurseReadOnly"],
        TYPE_VALUE_MAP["DistrictReadOnlyAdmin"],
        TYPE_VALUE_MAP["StateReadOnlyAdmin"],
    )

    TYPE_CHOICES = [(value, name) for name, value in TYPE_VALUE_MAP.items()]

    REVERSE_TYPE_MAP = reverse_choices(TYPE_CHOICES)

    user_type = models.IntegerField(choices=TYPE_CHOICES, blank=False)
    created_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users_created",
    )

    ward = models.ForeignKey(Ward, on_delete=models.PROTECT, null=True, blank=True)
    local_body = models.ForeignKey(
        LocalBody, on_delete=models.PROTECT, null=True, blank=True
    )
    district = models.ForeignKey(
        District, on_delete=models.PROTECT, null=True, blank=True
    )
    state = models.ForeignKey(State, on_delete=models.PROTECT, null=True, blank=True)

    phone_number = models.CharField(
        max_length=14, validators=[mobile_or_landline_number_validator]
    )
    alt_phone_number = models.CharField(
        max_length=14,
        validators=[mobile_validator],
        default=None,
        blank=True,
        null=True,
    )
    video_connect_link = models.URLField(blank=True, null=True)

    gender = models.IntegerField(choices=GENDER_CHOICES, blank=False)
    date_of_birth = models.DateField(null=True, blank=True)
    skills = models.ManyToManyField("Skill", through=UserSkill)
    home_facility = models.ForeignKey(
        "facility.Facility", on_delete=models.PROTECT, null=True, blank=True
    )
    weekly_working_hours = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(168)], null=True, blank=True
    )

    doctor_qualification = models.TextField(
        blank=False,
        null=True,
    )
    doctor_experience_commenced_on = models.DateField(
        default=None,
        blank=False,
        null=True,
    )
    doctor_medical_council_registration = models.CharField(
        max_length=255,
        default=None,
        blank=False,
        null=True,
    )

    verified = models.BooleanField(default=False)
    deleted = models.BooleanField(default=False)

    # Notification Data
    pf_endpoint = models.TextField(default=None, null=True)
    pf_p256dh = models.TextField(default=None, null=True)
    pf_auth = models.TextField(default=None, null=True)

    # Asset Fields

    asset = models.OneToOneField(
        "facility.Asset",
        default=None,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )

    objects = CustomUserManager()

    REQUIRED_FIELDS = [
        "email",
    ]

    CSV_MAPPING = {
        "username": "Username",
        "first_name": "First Name",
        "last_name": "Last Name",
        "phone_number": "Phone Number",
        "gender": "Gender",
        "date_of_birth": "Date of Birth",
        "verified": "verified",
        "local_body__name": "Local Body",
        "district__name": "District",
        "state__name": "State",
        "user_type": "User Type",
    }

    CSV_MAKE_PRETTY = {"user_type": (lambda x: User.REVERSE_TYPE_MAP[x])}

    @staticmethod
    def has_read_permission(request):
        return True

    def has_object_read_permission(self, request):
        return request.user.is_superuser or self == request.user

    @staticmethod
    def has_write_permission(request):
        try:
            return int(request.data["user_type"]) <= User.TYPE_VALUE_MAP["Volunteer"]
        except TypeError:
            return (
                User.TYPE_VALUE_MAP[request.data["user_type"]]
                <= User.TYPE_VALUE_MAP["Volunteer"]
            )
        except KeyError:
            # No user_type passed, the view shall raise a 400
            return True

    def has_object_write_permission(self, request):
        return request.user.is_superuser

    def has_object_update_permission(self, request):
        if request.user.is_superuser:
            return True
        if (
            request.data.get("district") or request.data.get("state")
        ) and self.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            # District/state admins shouldn't be able to edit their district/state, that'll practically give them
            # access to everything
            return False
        if request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            return self.state == request.user.state
        if request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            return self.district == request.user.district
        return self == request.user

    @staticmethod
    def has_add_user_permission(request):
        return request.user.is_superuser or request.user.verified

    @staticmethod
    def check_username_exists(username):
        return User.objects.get_entire_queryset().filter(username=username).exists()

    def delete(self, *args, **kwargs):
        self.deleted = True
        self.save()

    def get_absolute_url(self):
        return reverse("users:detail", kwargs={"username": self.username})

    def save(self, *args, **kwargs) -> None:
        """
        While saving, if the local body is not null, then district will be local body's district
        Overriding save will help in a collision where the local body's district and district fields are different.
        """
        if self.local_body is not None:
            self.district = self.local_body.district
        if self.district is not None:
            self.state = self.district.state
        super().save(*args, **kwargs)


class UserFacilityAllocation(models.Model):
    """
    This model tracks the allocation of a user to a facility for metabase analytics.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="+")
    facility = models.ForeignKey(
        "facility.Facility", on_delete=models.CASCADE, related_name="+"
    )
    start_date = models.DateTimeField(default=now)
    end_date = models.DateTimeField(null=True, blank=True)
