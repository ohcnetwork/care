from uuid import uuid4

from django.db import models
from django.db.models import JSONField

from care.facility.models.facility import Facility
from care.users.models import District, LocalBody

SUMMARY_CHOICES = (
    ("FacilityCapacity", "FacilityCapacity"),
    ("PatientSummary", "PatientSummary"),
    ("TestSummary", "TestSummary"),
    ("TriageSummary", "TriageSummary"),
)


class FacilityRelatedSummary(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)
    created_date = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_date = models.DateTimeField(auto_now=True, null=True, blank=True)
    facility = models.ForeignKey(
        Facility, on_delete=models.CASCADE, null=True, blank=True
    )
    s_type = models.CharField(choices=SUMMARY_CHOICES, max_length=100)
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

    def __str__(self):
        return f"FacilityRelatedSummary - {self.facility} - {self.s_type}"


DISTRICT_SUMMARY_CHOICES = (("PatientSummary", "PatientSummary"),)


class DistrictScopedSummary(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)
    created_date = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_date = models.DateTimeField(auto_now=True, null=True, blank=True)
    district = models.ForeignKey(
        District, on_delete=models.CASCADE, null=True, blank=True
    )
    s_type = models.CharField(choices=DISTRICT_SUMMARY_CHOICES, max_length=100)
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

    def __str__(self):
        return f"DistrictScopedSummary - {self.district} - {self.s_type}"


LSG_SUMMARY_CHOICES = (("PatientSummary", "PatientSummary"),)


class LocalBodyScopedSummary(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)
    created_date = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_date = models.DateTimeField(auto_now=True, null=True, blank=True)
    lsg = models.ForeignKey(LocalBody, on_delete=models.CASCADE, null=True, blank=True)
    s_type = models.CharField(choices=LSG_SUMMARY_CHOICES, max_length=100)
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

    def __str__(self):
        return f"LocalBodyScopedSummary - {self.lsg} - {self.s_type}"
