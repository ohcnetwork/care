from django.core.validators import RegexValidator
from django.db import models

phone_number_regex = RegexValidator(
    regex=r"^((\+91|91|0)[\- ]{0,1})?[456789]\d{9}$",
    message="Please Enter 10/11 digit mobile number or landline as 0<std code><phone number>",
    code="invalid_mobile",
)


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(deleted=False)


class FacilityBaseModel(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField(default=False)

    objects = SoftDeleteManager()

    class Meta:
        abstract = True

    def delete(self, *args):
        self.deleted = True
        self.save()
