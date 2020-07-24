from uuid import uuid4

from django.contrib.postgres.fields import JSONField
from django.db import models

from care.facility.models.facility import Facility

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
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, null=True, blank=True)
    s_type = models.CharField(choices=SUMMARY_CHOICES, max_length=100)
    data = JSONField(null=True, blank=True, default=dict)
