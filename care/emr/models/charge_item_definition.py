from django.db import models

from care.emr.models.base import SlugBaseModel


class ChargeItemDefinition(SlugBaseModel):
    facility = models.ForeignKey(
        "facility.Facility",
        on_delete=models.PROTECT,
    )
    version = models.IntegerField(default=1)
    status = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    slug = models.CharField(max_length=255)
    derived_from_uri = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    purpose = models.TextField(null=True, blank=True)
    price_components = models.JSONField(default=list)
    category = models.ForeignKey(
        "emr.ResourceCategory",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
