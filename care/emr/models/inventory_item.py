from decimal import Decimal

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
    net_content = models.DecimalField(
        default=Decimal(0), max_digits=20, decimal_places=6
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "location"],
                condition=models.Q(deleted=False),
                name="unique_active_inventory_product_location",
            )
        ]
