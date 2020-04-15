from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField

from care.users.models import District, LocalBody, State

User = get_user_model()


class TestingLab(models.Model):
    pincode_regex = RegexValidator(
        regex=r"^(\d{6}$)", message=_("Please enter a valid pincode."), code="invalid_pincode",
    )
    name = models.CharField(max_length=200)
    address = models.TextField()
    pincode = models.IntegerField(validators=[pincode_regex])
    phone_number = PhoneNumberField()
    local_body = models.ForeignKey(LocalBody, on_delete=models.SET_NULL, null=True, blank=True)
    district = models.ForeignKey(District, on_delete=models.SET_NULL, null=True, blank=True)
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True)
    testing_capacity_per_day = models.IntegerField(default=0, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    @staticmethod
    def has_object_read_permissions(self, request):
        """Allow all verified users to view"""
        return self.request.user.verified

    @staticmethod
    def has_object_write_permissions(self, request):
        """Allow anyone >= DistrictLabAdmin"""
        return request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]
