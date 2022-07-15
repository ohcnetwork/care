from django.contrib.auth.models import AbstractUser, UserManager
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from partial_index import PQ, PartialIndex

from care.utils.models.base import BaseModel


def reverse_choices(choices):
    output = {}
    for choice in choices:
        output[choice[0]] = choice[1]
    return output


GENDER_CHOICES = [(1, "Male"), (2, "Female"), (3, "Non-binary")]
REVERSE_GENDER_CHOICES = reverse_choices(GENDER_CHOICES)

phone_number_regex = RegexValidator(
    regex=r"^((\+91|91|0)[\- ]{0,1})?[456789]\d{9}$",
    message="Please Enter 10/11 digit mobile number or landline as 0<std code><phone number>",
    code="invalid_mobile",
)

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

    def create_superuser(self, username, email, password, **extra_fields):
        district = District.objects.all()[0]
        extra_fields["district"] = district
        extra_fields["age"] = 20
        extra_fields["phone_number"] = "+919696969696"
        extra_fields["gender"] = 3
        extra_fields["user_type"] = 40
        return super().create_superuser(username, email, password, **extra_fields)


class Skill(BaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True, default="")

    def __str__(self):
        return self.name


class UsernameValidator(UnicodeUsernameValidator):
    regex = r"^[\w.@+-]+[^.@+_-]$"
    message = _(
        "Please enter letters, digits and @ . + - _ only and username should not end with @ . + - or _"
    )


class UserSkill(BaseModel):
    user = models.ForeignKey("User", on_delete=models.CASCADE, null=True, blank=True)
    skill = models.ForeignKey("Skill", on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        indexes = [
            PartialIndex(fields=["skill", "user"], unique=True, where=PQ(deleted=False))
        ]


class User(AbstractUser):
    username_validator = UsernameValidator()
    username = models.CharField(
        _("username"),
        max_length=150,
        unique=True,
        help_text=_("150 characters or fewer. Letters, digits and @/./+/-/_ only."),
        validators=[username_validator],
        error_messages={"unique": _("A user with that username already exists.")},
    )

    TYPE_VALUE_MAP = {
        "Transportation": 2,
        "Pharmacist": 3,
        "Volunteer": 5,
        "StaffReadOnly": 9,
        "Staff": 10,
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

    phone_number = models.CharField(max_length=14, validators=[phone_number_regex])
    alt_phone_number = models.CharField(
        max_length=14,
        validators=[phone_number_regex],
        default=None,
        blank=True,
        null=True,
    )

    gender = models.IntegerField(choices=GENDER_CHOICES, blank=False)
    age = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(100)])
    skills = models.ManyToManyField("Skill", through=UserSkill)
    home_facility = models.ForeignKey("facility.Facility", on_delete=models.PROTECT, null=True, blank=True)
    verified = models.BooleanField(default=False)
    deleted = models.BooleanField(default=False)

    # Notification Data
    pf_endpoint = models.TextField(default=None, null=True)
    pf_p256dh = models.TextField(default=None, null=True)
    pf_auth = models.TextField(default=None, null=True)

    # Asset Fields

    asset = models.ForeignKey(
        "facility.Asset",
        default=None,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        unique=True,
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
        "age": "Age",
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
        if not self == request.user:
            return False
        if (
            request.data.get("district") or request.data.get("state")
        ) and self.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            # District/state admins shouldn't be able to edit their district/state, that'll practically give them
            # access to everything
            return False
        return True

    @staticmethod
    def has_add_user_permission(request):
        return request.user.is_superuser or request.user.verified

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
