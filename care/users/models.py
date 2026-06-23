import secrets
import string
import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from care.utils.models.base import BaseFlag, BaseModel
from care.utils.models.choices import reverse_choices
from care.utils.models.validators import (
    UsernameValidator,
    mobile_or_landline_number_validator,
    mobile_validator,
)
from care.utils.registries.feature_flag import FlagName, FlagType

USER_FLAG_CACHE_KEY = "user_flag_cache:{user_id}:{flag_name}"
USER_ALL_FLAGS_CACHE_KEY = "user_all_flags_cache:{user_id}"
USER_FLAG_CACHE_TTL = 60 * 60 * 24  # 1 Day


GENDER_CHOICES = [(1, "Male"), (2, "Female"), (3, "Non-binary")]
REVERSE_GENDER_CHOICES = reverse_choices(GENDER_CHOICES)


class CustomUserManager(UserManager):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(deleted=False)

    def get_entire_queryset(self):
        return super().get_queryset()

    def create_superuser(self, username, email, password, **extra_fields):
        extra_fields["phone_number"] = "+919696969696"
        extra_fields["gender"] = "non_binary"
        extra_fields["user_type"] = "administrator"
        return super().create_superuser(username, email, password, **extra_fields)

    def make_random_password(
        self,
        length: int = 10,
        secure_random: bool = True,
        allowed_chars: str = string.ascii_letters + string.digits + string.punctuation,
    ) -> str:
        """
        Generate a random password with the specified length and allowed characters.

        If secure_random is True the allowed_chars parameter is ignored and,
        the generated password will contain:
        - At least one lowercase letter.
        - At least one uppercase letter.
        - At least length // 4 digits.
        """
        if secure_random:
            allowed_chars = string.ascii_letters + string.digits + string.punctuation
            while True:
                password = "".join(secrets.choice(allowed_chars) for i in range(length))
                if (
                    any(c.islower() for c in password)
                    and any(c.isupper() for c in password)
                    and sum(c.isdigit() for c in password) >= (length // 4)
                ):
                    break
        else:
            password = "".join(secrets.choice(allowed_chars) for _ in range(length))
        return password


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

    user_type = models.CharField(max_length=100, null=True, blank=True)
    created_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users_created",
    )

    geo_organization = models.ForeignKey(
        "emr.Organization", on_delete=models.SET_NULL, null=True, blank=True
    )

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

    old_gender = models.IntegerField(
        choices=GENDER_CHOICES, blank=True, null=True, default=None
    )
    gender = models.CharField(max_length=100, blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    profile_picture_url = models.CharField(
        blank=True, null=True, default=None, max_length=500
    )
    skills = models.ManyToManyField("Skill", through=UserSkill)
    home_facility = models.ForeignKey(
        "facility.Facility", on_delete=models.PROTECT, null=True, blank=True
    )
    weekly_working_hours = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(168)], null=True, blank=True
    )

    qualification = models.TextField(
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

    prefix = models.CharField(max_length=10, blank=True, null=True)
    suffix = models.CharField(max_length=50, blank=True, null=True)

    is_service_account = models.BooleanField(default=False)

    verified = models.BooleanField(default=False)
    deleted = models.BooleanField(default=False)

    # Notification Data
    pf_endpoint = models.TextField(default=None, null=True)
    pf_p256dh = models.TextField(default=None, null=True)
    pf_auth = models.TextField(default=None, null=True)
    totp_secret = models.TextField(blank=True, null=True)
    mfa_settings = models.JSONField(default=dict, blank=True)

    # Preferences

    preferences = models.JSONField(default=dict)

    cached_role_orgs = models.JSONField(default=None, null=True, blank=True)

    objects = CustomUserManager()

    REQUIRED_FIELDS = [
        "email",
    ]

    def get_cached_role_orgs(self):
        from care.emr.models.organization import OrganizationUser

        if self.cached_role_orgs is not None:
            return self.cached_role_orgs
        data = OrganizationUser.get_cached_role_orgs(self.id)
        self.cached_role_orgs = data
        self.save(update_fields=["cached_role_orgs"])
        return data

    def read_profile_picture_url(self):
        if self.profile_picture_url:
            if settings.FACILITY_CDN:
                return f"{settings.FACILITY_CDN}/{self.profile_picture_url}"
            return f"{settings.FACILITY_S3_BUCKET_EXTERNAL_ENDPOINT}/{settings.FACILITY_S3_BUCKET}/{self.profile_picture_url}"
        return None

    def is_mfa_enabled(self):
        return bool(self.mfa_settings.get("totp", {}).get("enabled", False))

    @property
    def full_name(self):
        name_parts = []
        if self.prefix:
            name_parts.append(self.prefix)
        name_parts.append(self.get_full_name())
        if self.suffix:
            name_parts.append(self.suffix)
        return " ".join(name_parts)

    @staticmethod
    def check_username_exists(username):
        return User.objects.get_entire_queryset().filter(username=username).exists()

    def get_absolute_url(self):
        return reverse("users:detail", kwargs={"username": self.username})

    def get_all_flags(self):
        return UserFlag.get_all_flags(self.id)


class PlugConfig(models.Model):
    slug = models.CharField(max_length=255, unique=True)
    meta = models.JSONField(default=dict)

    def __str__(self):
        return self.slug


class UserFlag(BaseFlag):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False, blank=False)

    cache_key_template = "user_flag_cache:{entity_id}:{flag_name}"
    all_flags_cache_key_template = "user_all_flags_cache:{entity_id}"
    flag_type = FlagType.USER
    entity_field_name = "user"

    def __str__(self):
        return f"User Flag: {self.user.get_full_name()} - {self.flag}"

    class Meta:
        verbose_name = "User Flag"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "flag"],
                condition=models.Q(deleted=False),
                name="unique_user_flag",
            )
        ]

    @classmethod
    def check_user_has_flag(cls, user_id: int, flag_name: FlagName) -> bool:
        return cls.check_entity_has_flag(user_id, flag_name)

    @classmethod
    def get_all_flags(cls, user_id: int) -> tuple[FlagName]:
        return super().get_all_flags(user_id)
