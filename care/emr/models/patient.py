from datetime import date

from dateutil.relativedelta import relativedelta
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator
from django.db import models
from django.template.defaultfilters import pluralize
from django.utils import timezone

from care.emr.models import EMRBaseModel
from care.users.models import User
from care.utils.models.validators import mobile_or_landline_number_validator


class Patient(EMRBaseModel):
    name = models.CharField(max_length=200, default="")
    gender = models.CharField(max_length=35, default="")

    phone_number = models.CharField(
        max_length=14, validators=[mobile_or_landline_number_validator], default=""
    )

    emergency_phone_number = models.CharField(
        max_length=14, validators=[mobile_or_landline_number_validator], default=""
    )
    address = models.TextField(default="")
    permanent_address = models.TextField(default="")

    pincode = models.IntegerField(default=0, blank=True, null=True)

    date_of_birth = models.DateField(default=None, null=True)
    year_of_birth = models.IntegerField(validators=[MinValueValidator(1900)], null=True)
    deceased_datetime = models.DateTimeField(default=None, null=True, blank=True)

    marital_status = models.CharField(max_length=50, default="")

    blood_group = models.CharField(max_length=16)

    geo_organization = models.ForeignKey(
        "emr.Organization", on_delete=models.SET_NULL, null=True, blank=True
    )

    organization_cache = ArrayField(models.IntegerField(), default=list)

    users_cache = ArrayField(models.IntegerField(), default=list)

    def get_age(self) -> str:
        start = self.date_of_birth or date(self.year_of_birth, 1, 1)
        end = (self.deceased_datetime or timezone.now()).date()

        delta = relativedelta(end, start)

        if delta.years > 0:
            year_str = f"{delta.years} year{pluralize(delta.years)}"
            return f"{year_str}"

        if delta.months > 0:
            month_str = f"{delta.months} month{pluralize(delta.months)}"
            day_str = (
                f" {delta.days} day{pluralize(delta.days)}" if delta.days > 0 else ""
            )
            return f"{month_str}{day_str}"

        if delta.days > 0:
            return f"{delta.days} day{pluralize(delta.days)}"

        return "0 days"

    def rebuild_organization_cache(self):
        organization_parents = []
        if self.geo_organization:
            organization_parents.extend(self.geo_organization.parent_cache)
            organization_parents.append(self.geo_organization.id)
        if self.id:
            for patient_organization in PatientOrganization.objects.filter(
                patient_id=self.id
            ):
                organization_parents.extend(
                    patient_organization.organization.parent_cache
                )
                organization_parents.append(patient_organization.id)

        self.organization_cache = list(set(organization_parents))

    def rebuild_users_cache(self):
        if self.id:
            users = list(
                PatientUser.objects.filter(patient=self).values_list(
                    "user_id", flat=True
                )
            )
            self.users_cache = users

    def save(self, *args, **kwargs) -> None:
        if self.date_of_birth and not self.year_of_birth:
            self.year_of_birth = self.date_of_birth.year
        super().save(*args, **kwargs)
        self.rebuild_organization_cache()
        self.rebuild_users_cache()
        super().save(update_fields=["organization_cache", "users_cache"])


class PatientOrganization(EMRBaseModel):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    organization = models.ForeignKey("emr.Organization", on_delete=models.CASCADE)
    # TODO : Add Role here to deny certain permissions for certain organizations

    def save(self, *args, **kwargs) -> None:
        super().save(*args, **kwargs)
        self.patient.save()


class PatientUser(EMRBaseModel):
    """
    Add a user that can access the patient
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    role = models.ForeignKey("security.RoleModel", on_delete=models.PROTECT)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.patient.save()
