from uuid import uuid4

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models import JSONField

from care.facility.models.facility import Facility
from care.users.models import District, LocalBody


# SUMMARY_CHOICES = (
#     ("FacilityCapacity", "FacilityCapacity"),
#     ("PatientSummary", "PatientSummary"),
#     ("TestSummary", "TestSummary"),
#     ("TriageSummary", "TriageSummary"),
# )

class SummaryChoices(models.TextChoices):
    FACILITY_CAPACITY = "FacilityCapacity", _("Facility Capacity")
    PATIENT_SUMMARY = "PatientSummary", _("Patient Summary")
    TEST_SUMMARY = "TestSummary", _("Test Summary")
    TRIAGE_SUMMARY = "TriageSummary", _("Triage Summary")


class FacilityRelatedSummary(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)
    created_date = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_date = models.DateTimeField(auto_now=True, null=True, blank=True)
    facility = models.ForeignKey(
        Facility, on_delete=models.CASCADE, null=True, blank=True
    )
    s_type = models.CharField(choices=SummaryChoices.choices, max_length=100)
    data = JSONField(null=True, blank=True, default=dict)

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "-modified_date",
                ]
            ),
            models.Index(
                fields=[
                    "-created_date",
                ]
            ),
            models.Index(
                fields=[
                    "s_type",
                ]
            ),
            models.Index(fields=["-created_date", "s_type"]),
        ]


# DISTRICT_SUMMARY_CHOICES = (("PatientSummary", "PatientSummary"),)
class DistrictSummaryChoices(models.TextChoices):
    PATIENT_SUMMARY = "PatientSummary", _("Patient Summary")


class DistrictScopedSummary(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)
    created_date = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_date = models.DateTimeField(auto_now=True, null=True, blank=True)
    district = models.ForeignKey(
        District, on_delete=models.CASCADE, null=True, blank=True
    )
    s_type = models.CharField(choices=DistrictSummaryChoices.choices, max_length=100)
    data = JSONField(null=True, blank=True, default=dict)

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "-modified_date",
                ]
            ),
            models.Index(
                fields=[
                    "-created_date",
                ]
            ),
            models.Index(
                fields=[
                    "s_type",
                ]
            ),
            models.Index(fields=["-created_date", "s_type"]),
        ]


class LSGSummaryChoices(models.TextChoices):
    PATIENT_SUMMARY = "PatientSummary", _("Patient Summary")


class LocalBodyScopedSummary(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)
    created_date = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_date = models.DateTimeField(auto_now=True, null=True, blank=True)
    lsg = models.ForeignKey(LocalBody, on_delete=models.CASCADE, null=True, blank=True)
    s_type = models.CharField(choices=LSGSummaryChoices.choices, max_length=100)
    data = JSONField(null=True, blank=True, default=dict)

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "-modified_date",
                ]
            ),
            models.Index(
                fields=[
                    "-created_date",
                ]
            ),
            models.Index(
                fields=[
                    "s_type",
                ]
            ),
            models.Index(fields=["-created_date", "s_type"]),
        ]
