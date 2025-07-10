from django.db import models

from care.emr.models import EMRBaseModel


class Product(EMRBaseModel):
    facility = models.ForeignKey("facility.Facility", on_delete=models.PROTECT)
    product_knowledge = models.ForeignKey(
        "emr.ProductKnowledge", on_delete=models.PROTECT
    )
    charge_item_definition = models.ForeignKey(
        "emr.ChargeItemDefinition", on_delete=models.PROTECT, null=True, blank=True
    )
    status = models.CharField(max_length=255)
    product_type = models.CharField(max_length=255)
    batch = models.JSONField(default=dict, null=True, blank=True)
    expiration_date = models.DateTimeField(default=None, null=True, blank=True)
