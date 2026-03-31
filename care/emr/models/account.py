from django.contrib.postgres.fields import ArrayField
from django.db import models

from care.emr.models.base import EMRBaseModel


class Account(EMRBaseModel):
    facility = models.ForeignKey(
        "facility.Facility",
        on_delete=models.PROTECT,
        help_text="The facility where this account was created.",
    )
    status = models.CharField(max_length=255)
    billing_status = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    service_period = models.JSONField(default=dict)
    description = models.TextField(null=True, blank=True)
    patient = models.ForeignKey("emr.Patient", on_delete=models.PROTECT)
    cached_items = models.JSONField(default=dict)
    total_net = models.DecimalField(
        default=0, max_digits=20, decimal_places=6,
        help_text="Total amount after discounts, before tax.",
    )
    total_gross = models.DecimalField(
        default=0, max_digits=20, decimal_places=6,
        help_text="Total amount before any discounts or adjustments.",
    )
    total_paid = models.DecimalField(
        default=0, max_digits=20, decimal_places=6,
        help_text="Total amount received from the patient so far.",
    )
    total_balance = models.DecimalField(
        default=0, max_digits=20, decimal_places=6,
        help_text="Outstanding amount owed."
    )
    total_price_components = models.JSONField(default=dict)
    calculated_at = models.DateTimeField(
        null=True, blank=True, default=None,
        help_text="Timestamp of the last billing recalculation. Null if never calculated.",
        )
    total_billable_charge_items = models.DecimalField(
        default=0, max_digits=20, decimal_places=6,
        help_text="Sum of all individual charge items eligible for billing.",
    )
    tags = ArrayField(models.IntegerField(), default=list)
    extensions = models.JSONField(default=dict)
    primary_encounter = models.ForeignKey(
        "emr.Encounter", on_delete=models.SET_NULL, null=True, blank=True, default=None
    )
