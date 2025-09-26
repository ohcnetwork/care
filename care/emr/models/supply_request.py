from django.contrib.postgres.fields import ArrayField
from django.db import models

from care.emr.models import EMRBaseModel


class SupplyRequest(EMRBaseModel):
    status = models.CharField(max_length=255)
    quantity = models.FloatField(null=True, blank=True)
    supplied_item_condition = models.CharField(max_length=255)
    intent = models.CharField(max_length=255)
    category = models.CharField(max_length=255)
    priority = models.CharField(max_length=255)
    item = models.ForeignKey("emr.ProductKnowledge", on_delete=models.CASCADE)
    deliver_from = models.ForeignKey(
        "emr.FacilityLocation",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="origin_requests",
    )
    deliver_to = models.ForeignKey(
        "emr.FacilityLocation",
        related_name="destination_requests",
        on_delete=models.CASCADE,
    )
    supplier = models.ForeignKey(
        "emr.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="supply_requests",
    )
    reason = models.CharField(max_length=255)

    order = models.ForeignKey(
        "emr.RequestOrder",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )


class RequestOrder(EMRBaseModel):
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=255)
    note = models.TextField(null=True, blank=True)
    location = models.ForeignKey("emr.FacilityLocation", on_delete=models.CASCADE)
    tags = ArrayField(models.IntegerField(), default=list)
