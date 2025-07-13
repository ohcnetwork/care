from django.db import models

from care.emr.models import EMRBaseModel


class InventoryItem(EMRBaseModel):
    location = models.ForeignKey(
        "emr.FacilityLocation",
        on_delete=models.PROTECT,
    )
    product = models.ForeignKey(
        "emr.Product",
        on_delete=models.PROTECT,
    )
    status = models.CharField(max_length=255)
    net_content = models.FloatField(default=0)
