from django.contrib.auth.models import AbstractUser, UserManager
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse

from apps.accounts import constants as accounts_constants
from apps.commons import (
    constants as commons_constants,
    validators as commons_validators,
)


class State(models.Model):
    """
    Model to store States
    """
    name = models.CharField(max_length=commons_constants.FIELDS_CHARACTER_LIMITS['NAME'], help_text='Name of the State')

    def __str__(self):
        return f"{self.name}"


class District(models.Model):
    """
    Model to store districts
    """
    state = models.ForeignKey(State, on_delete=models.PROTECT)
    name = models.CharField(
        max_length=commons_constants.FIELDS_CHARACTER_LIMITS['NAME'], help_text='Name of the District'
    )

    def __str__(self):
        return f"{self.name}"


class LocalBody(models.Model):
    """
    Model to store details of local bodies
    """

    district = models.ForeignKey(District, on_delete=models.PROTECT)
    name = models.CharField(
        max_length=commons_constants.FIELDS_CHARACTER_LIMITS['NAME'], help_text='Name of the Local Body'
    )
    body_type = models.PositiveIntegerField(
        choices=accounts_constants.LOCAL_BODY_CHOICES, help_text='denotes the type of local body'
    )
    localbody_code = models.CharField(
        max_length=commons_constants.FIELDS_CHARACTER_LIMITS['LOCALBODY_CODE'],
        blank=True, help_text='Code of local body'
    )

    class Meta:
        unique_together = ('district', 'body_type', 'name',)

    def __str__(self):
        return f"{self.name} ({self.body_type})"


class Skill(models.Model):
    """
    Model to store skills of auser
    """
    name = models.CharField(max_length=commons_constants.FIELDS_CHARACTER_LIMITS['NAME'], help_text='Name of the skill')
    description = models.TextField(help_text='description of skill')

    def __str__(self):
        return self.name


class CustomUserManager(UserManager):
    """
    Customer object manager for users
    """
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(active=True)


class User(AbstractUser):
    """
    Model to represent a user
    """
    user_type = models.PositiveIntegerField(choices=accounts_constants.USER_TYPE_VALUES, blank=False)
    local_body = models.ForeignKey(LocalBody, on_delete=models.PROTECT, null=True, blank=True)
    district = models.ForeignKey(District, on_delete=models.PROTECT, null=True, blank=True)
    state = models.ForeignKey(State, on_delete=models.PROTECT, null=True, blank=True)
    phone_number = models.CharField(
        max_length=commons_constants.FIELDS_CHARACTER_LIMITS['PHONE_NUMBER'],
        validators=[commons_validators.phone_number_regex]
    )
    gender = models.IntegerField(choices=commons_constants.GENDER_CHOICES, blank=False)
    age = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(100)])
    skill = models.ForeignKey(Skill, on_delete=models.SET_NULL, null=True, blank=True)
    verified = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    REQUIRED_FIELDS = ['user_type', 'email', 'phone_number', 'age', 'gender']

    objects = CustomUserManager()

    @staticmethod
    def has_read_permission(request):
        return True

    def has_object_read_permission(self, request):
        return request.user.is_superuser or self == request.user

    @staticmethod
    def has_write_permission(request):
        try:
            return int(request.data["user_type"]) <= accounts_constants.VOLUNTEER
        except TypeError:
            return accounts_constants.USER_TYPE_VALUES[request.data["user_type"]] <= accounts_constants.VOLUNTEER
        except KeyError:
            # No user_type passed, the view shall raise a 400
            return True

    def has_object_write_permission(self, request):
        return request.user.is_superuser

    def has_object_update_permission(self, request):
        if request.user.is_superuser:
            return True
        if not self == request.user or ((
            request.data.get("district") or request.data.get("state")
        ) and self.user_type >= accounts_constants.DISTRICT_LAB_ADMIN):
            # District/state admins shouldn't be able to edit their district/state, that'll practically give them
            # access to everything
            return False
        return True

    @staticmethod
    def has_add_user_permission(request):
        return request.user.is_superuser or request.user.verified

    def delete(self, *args, **kwargs):
        self.active = True
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
