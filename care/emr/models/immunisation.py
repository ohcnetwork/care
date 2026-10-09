from django.db import models

from care.emr.models.base import EMRBaseModel


class ImmunizationRecommendation(EMRBaseModel):
    codes = models.JSONField(default=list)
    diseases = models.JSONField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    earliest_date = models.DateField(null=True, blank=True)
    overdue_date = models.DateField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    series = models.CharField(max_length=255, null=True, blank=True)
    dose_number = models.CharField(max_length=255, null=True, blank=True)
    series_number = models.CharField(max_length=255, null=True, blank=True)
    forecast_status = models.CharField(max_length=100)
    is_group = models.BooleanField()
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )
    patient = models.ForeignKey("emr.Patient", on_delete=models.CASCADE)
    encounter = models.ForeignKey(
        "emr.Encounter", on_delete=models.CASCADE, null=True, blank=True
    )


class ImmunizationPolicy(EMRBaseModel):
    policy_template = models.JSONField(default=dict)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    facility = models.ForeignKey(
        "facility.Facility",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )


class Immunization(EMRBaseModel):
    status = models.CharField(max_length=100)
    reason = models.CharField(max_length=100, null=True, blank=True)
    code = models.JSONField(default=dict)
    occurrence = models.DateTimeField(null=True, blank=True)
    primary_source = models.BooleanField()
    site = models.JSONField(null=True, blank=True)
    route = models.JSONField(null=True, blank=True)
    dose_quantity = models.JSONField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)
    is_subpotent = models.BooleanField(null=True, blank=True)
    subpotent_reason = models.TextField(null=True, blank=True)
    recommendation = models.ForeignKey(
        "emr.ImmunizationRecommendation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    product = models.ForeignKey(
        "emr.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    location = models.ForeignKey(
        "emr.FacilityLocation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    administered_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    encounter = models.ForeignKey("emr.Encounter", on_delete=models.CASCADE)
    patient = models.ForeignKey("emr.Patient", on_delete=models.CASCADE)
    facility = models.ForeignKey("facility.Facility", on_delete=models.PROTECT)
