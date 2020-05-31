from django.contrib.auth.models import AbstractUser, UserManager
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import ugettext as _

from simple_history.models import HistoricalRecords

from apps.accounts import constants as accounts_constants
from apps.commons import (
    constants as commons_constants,
    models as commons_models,
    validators as commons_validators,
)


class State(models.Model):
    """
    Model to store States
    """

    name = models.CharField(
        max_length=commons_constants.FIELDS_CHARACTER_LIMITS["NAME"],
        help_text="Name of the State",
    )

    def __str__(self):
        return f"{self.name}"


class District(models.Model):
    """
    Model to store districts
    """

    state = models.ForeignKey(State, on_delete=models.PROTECT)
    name = models.CharField(
        max_length=commons_constants.FIELDS_CHARACTER_LIMITS["NAME"],
        help_text="Name of the District",
    )

    def __str__(self):
        return f"{self.name}"


class LocalBody(models.Model):
    """
    Model to store details of local bodies
    """

    district = models.ForeignKey(District, on_delete=models.PROTECT)
    name = models.CharField(
        max_length=commons_constants.FIELDS_CHARACTER_LIMITS["NAME"],
        help_text="Name of the Local Body",
    )
    body_type = models.PositiveIntegerField(
        choices=accounts_constants.LOCAL_BODY_CHOICES,
        help_text="denotes the type of local body",
    )
    localbody_code = models.CharField(
        max_length=commons_constants.FIELDS_CHARACTER_LIMITS["LOCALBODY_CODE"],
        blank=True,
        help_text="Code of local body",
    )

    class Meta:
        unique_together = (
            "district",
            "body_type",
            "name",
        )

    def __str__(self):
        return f"{self.name} ({self.body_type})"


class Skill(models.Model):
    """
    Model to store skills of auser
    """

    name = models.CharField(
        max_length=commons_constants.FIELDS_CHARACTER_LIMITS["NAME"],
        help_text="Name of the skill",
    )
    description = models.TextField(help_text="description of skill")

    def __str__(self):
        return self.name


class CustomUserManager(UserManager):
    """
    Customer object manager for users
    """

    def get_queryset(self):
        return commons_models.SoftDeleteQuerySet(self.model, using=self._db).filter(
            active=True
        )

    def hard_delete(self):
        return self.get_queryset().hard_delete()


class UserType(models.Model):
    """
    Model to stores the types of user
    """

    name = models.CharField(
        max_length=commons_constants.FIELDS_CHARACTER_LIMITS["NAME"],
        help_text="Type of User",
    )

    def __str__(self):
        return self.name


class User(AbstractUser, commons_models.SoftDeleteTimeStampedModel):
    """
    Model to represent a user
    """

    # Drop first_name and last_name from base class
    first_name = None
    last_name = None
    name = models.CharField(_("name"), max_length=255)
    email = models.EmailField(_("email address"), unique=True)
    user_type = models.ForeignKey(
        UserType, on_delete=models.CASCADE, null=True, blank=True
    )
    phone_number = models.CharField(
        max_length=commons_constants.FIELDS_CHARACTER_LIMITS["PHONE_NUMBER"],
        validators=[commons_validators.phone_number_regex],
        null=True,
        blank=True,
    )
    preferred_districts = models.ManyToManyField(
        District,
        through="accounts.UserDistrictPreference",
        related_name="preferred_users",
    )
    history = HistoricalRecords()

    REQUIRED_FIELDS = ("email",)

    objects = CustomUserManager()

    def __str__(self):
        return self.email


class UserDistrictPreference(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    district = models.ForeignKey(District, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("user", "district")
