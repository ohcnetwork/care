from django.contrib.postgres.fields import ArrayField
from django.db import models

from care.emr.models.base import EMRBaseModel


class ChargeItem(EMRBaseModel):
    facility = models.ForeignKey(
        "facility.Facility",
        on_delete=models.PROTECT,
    )
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    patient = models.ForeignKey("emr.Patient", on_delete=models.CASCADE)
    encounter = models.ForeignKey("emr.Encounter", on_delete=models.CASCADE)
    charge_item_definition = models.ForeignKey(
        "emr.ChargeItemDefinition", on_delete=models.CASCADE, null=True, blank=True
    )
    account = models.ForeignKey("emr.Account", on_delete=models.CASCADE)
    status = models.CharField(max_length=255)
    code = models.JSONField(null=True, blank=True)
    quantity = models.DecimalField(
        null=True, blank=True, max_digits=10, decimal_places=2
    )
    unit_price_components = models.JSONField(null=True, blank=True)
    total_price_components = models.JSONField(null=True, blank=True)
    total_price = models.DecimalField(
        null=True, blank=True, max_digits=10, decimal_places=2
    )
    note = models.TextField(null=True, blank=True)
    override_reason = models.JSONField(null=True, blank=True)
    service_resource = models.CharField(
        max_length=255, null=True, blank=True, default=None
    )
    service_resource_id = models.CharField(
        max_length=255, null=True, blank=True, default=None
    )
    paid_invoice = models.ForeignKey(
        "emr.Invoice",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        default=None,
    )
    tags = ArrayField(models.IntegerField(), default=list)
