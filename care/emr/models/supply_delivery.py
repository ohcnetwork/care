from django.contrib.postgres.fields import ArrayField
from django.db import models

from care.emr.models import EMRBaseModel


class SupplyDelivery(EMRBaseModel):
    status = models.CharField(max_length=255)
    supplied_item_pack_quantity = models.IntegerField(
        null=True, blank=True, default=None
    )
    supplied_item_pack_size = models.IntegerField(null=True, blank=True, default=None)
    supplied_item_quantity = models.DecimalField(
        null=True, blank=True, max_digits=20, decimal_places=6
    )
    supplied_item = models.ForeignKey(
        "emr.Product", on_delete=models.CASCADE, null=True, blank=True
    )
    supplied_inventory_item = models.ForeignKey(
        "emr.InventoryItem", on_delete=models.CASCADE, null=True, blank=True
    )
    supplied_item_condition = models.CharField(max_length=255)
    delivery_type = models.CharField(max_length=255)
    supply_request = models.ForeignKey(
        "emr.SupplyRequest", on_delete=models.CASCADE, null=True, blank=True
    )
    order = models.ForeignKey(
        "emr.DeliveryOrder",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    extensions = models.JSONField(default=dict)
    total_purchase_price = models.DecimalField(
        null=True, blank=True, max_digits=20, decimal_places=6
    )


class DeliveryOrder(EMRBaseModel):
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=255)
    note = models.TextField(null=True, blank=True)
    tags = ArrayField(models.IntegerField(), default=list)
    supplier = models.ForeignKey(
        "emr.Organization", on_delete=models.CASCADE, null=True, blank=True
    )
    origin = models.ForeignKey(
        "emr.FacilityLocation",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="origin_delivery_orders",
    )
    destination = models.ForeignKey(
        "emr.FacilityLocation",
        related_name="destination_delivery_orders",
        on_delete=models.CASCADE,
    )
    extensions = models.JSONField(default=dict)
    patient = models.ForeignKey(
        "emr.Patient", on_delete=models.PROTECT, null=True, blank=True, default=None
    )
    patient_invoice = models.ForeignKey(
        "emr.Invoice", on_delete=models.PROTECT, null=True, blank=True, default=None
    )
