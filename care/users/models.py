from django.contrib.auth.models import AbstractUser, UserManager
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.urls import reverse


def reverse_choices(choices):
    output = {}
    for choice in choices:
        output[choice[0]] = choice[1]
    return output


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
REVERSE_GENDER_CHOICES = reverse_choices(GENDER_CHOICES)

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
        return qs.filter(deleted=False).select_related("local_body", "district", "state")

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


class User(AbstractUser):
    TYPE_VALUE_MAP = {
        "Doctor": 5,
        "Staff": 10,
        "Patient": 15,
        "Volunteer": 20,
        "DistrictLabAdmin": 25,
        "DistrictAdmin": 30,
        "StateLabAdmin": 35,
        "StateAdmin": 40,
    }

    TYPE_CHOICES = [(value, name) for name, value in TYPE_VALUE_MAP.items()]

    user_type = models.IntegerField(choices=TYPE_CHOICES, blank=False)

    local_body = models.ForeignKey(LocalBody, on_delete=models.PROTECT, null=True, blank=True)
    district = models.ForeignKey(District, on_delete=models.PROTECT, null=True, blank=True)
    state = models.ForeignKey(State, on_delete=models.PROTECT, null=True, blank=True)

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
            return User.TYPE_VALUE_MAP[request.data["user_type"]] <= User.TYPE_VALUE_MAP["Volunteer"]
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
        if (request.data.get("district") or request.data.get("state")) and self.user_type >= User.TYPE_VALUE_MAP[
            "DistrictLabAdmin"
        ]:
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
