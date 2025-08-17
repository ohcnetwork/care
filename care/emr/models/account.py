from django.db import models

from care.emr.models.base import EMRBaseModel


class Account(EMRBaseModel):
    facility = models.ForeignKey(
        "facility.Facility",
        on_delete=models.PROTECT,
    )
    status = models.CharField(max_length=255)
    billing_status = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    service_period = models.JSONField(default=dict)
    description = models.TextField(null=True, blank=True)
    patient = models.ForeignKey("emr.Patient", on_delete=models.PROTECT)
    cached_items = models.JSONField(default=dict)
    total_net = models.DecimalField(default=0, max_digits=10, decimal_places=2)
    total_gross = models.DecimalField(default=0, max_digits=10, decimal_places=2)
    total_paid = models.DecimalField(default=0, max_digits=10, decimal_places=2)
    total_balance = models.DecimalField(default=0, max_digits=10, decimal_places=2)
    total_price_components = models.JSONField(default=dict)
    calculated_at = models.DateTimeField(null=True, blank=True, default=None)
