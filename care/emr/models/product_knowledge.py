from django.db import models

from care.emr.models.base import SlugBaseModel


class ProductKnowledge(SlugBaseModel):
    facility = models.ForeignKey(
        "facility.Facility", on_delete=models.PROTECT, null=True, blank=True
    )
    slug = models.CharField(max_length=255)
    alternate_identifier = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=255)
    product_type = models.CharField(max_length=255)
    code = models.JSONField(default=dict, null=True, blank=True)
    name = models.CharField(max_length=255)
    names = models.JSONField(default=list, null=True, blank=True)
    storage_guidelines = models.JSONField(default=list, null=True, blank=True)
    definitional = models.JSONField(default=dict, null=True, blank=True)
    base_unit = models.JSONField(default=dict, null=True, blank=True)
    category = models.ForeignKey(
        "emr.ResourceCategory",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
