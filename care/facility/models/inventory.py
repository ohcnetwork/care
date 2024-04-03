from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Index

from care.facility.models import FacilityBaseModel
from care.facility.models.mixins.permissions.facility import (
    FacilityRelatedPermissionMixin,
)

User = get_user_model()


class FacilityInventoryItemTag(models.Model):
    """
    This Model stores tags of Inventory Items
    """

    name = models.CharField(max_length=255, blank=False, null=False)

    def __str__(self):
        return self.name


class FacilityInventoryUnit(models.Model):
    """
    This Model Stores Possible Units for items that are managed in this portal
    """

    name = models.CharField(max_length=255, blank=False, null=False, unique=True)

    def __str__(self):
        return self.name


class FacilityInventoryUnitConverter(models.Model):
    """
    Since Multiple Units are used for many items, it makes sense for the backend to store different units and
    interchange between them when needed

    This Model stores all the conversion metrics
    """

    from_unit = models.ForeignKey(
        FacilityInventoryUnit,
        related_name="from_unit",
        on_delete=models.CASCADE,
        null=False,
        blank=False,
    )
    to_unit = models.ForeignKey(
        FacilityInventoryUnit,
        related_name="to_unit",
        on_delete=models.CASCADE,
        null=False,
        blank=False,
    )
    multiplier = models.FloatField(blank=False, null=False)

    def __str__(self):
        return (
            "1 "
            + str(self.to_unit)
            + " x "
            + str(self.multiplier)
            + " =  1"
            + str(self.from_unit)
        )


class FacilityInventoryItem(models.Model):
    """
    This Model stores all the different items that can be added in a facility.
    the min_quantity describes the items that are at the verse of finishing up
    """

    name = models.CharField(max_length=1000, blank=False, null=False)
    default_unit = models.ForeignKey(
        FacilityInventoryUnit,
        related_name="default_unit",
        on_delete=models.SET_NULL,
        null=True,
        blank=False,
    )
    allowed_units = models.ManyToManyField(
        FacilityInventoryUnit, related_name="allowed_units"
    )
    tags = models.ManyToManyField(FacilityInventoryItemTag)
    description = models.TextField(blank=True)
    min_quantity = models.FloatField()

    def __str__(self):
        return self.name


class FacilityInventoryLog(FacilityBaseModel, FacilityRelatedPermissionMixin):
    """
    This items logs each inventory item added or taken from a particular facility, this is done so that each
    inventory change is accounted for.

    is_incoming is True if the items are added into the Facility and False if not
    """

    facility = models.ForeignKey(
        "Facility", on_delete=models.CASCADE, null=False, blank=False
    )
    item = models.ForeignKey(
        FacilityInventoryItem, on_delete=models.SET_NULL, null=True, blank=False
    )
    current_stock = models.FloatField(default=0)
    quantity_in_default_unit = models.FloatField(default=0)
    quantity = models.FloatField(default=0, validators=[MinValueValidator(0.0)])
    unit = models.ForeignKey(
        FacilityInventoryUnit, on_delete=models.SET_NULL, null=True, blank=False
    )
    is_incoming = models.BooleanField()
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    probable_accident = models.BooleanField(default=False)


class FacilityInventorySummary(FacilityBaseModel, FacilityRelatedPermissionMixin):
    """
    This Model summarises the items capacity for each item for each facility so that it is not recalculated each time
    is_low is a flag that is set if the item is below its minimum quantity set in the Inventory Item.
    """

    facility = models.ForeignKey(
        "Facility", on_delete=models.CASCADE, null=False, blank=False
    )
    item = models.ForeignKey(
        FacilityInventoryItem, on_delete=models.SET_NULL, null=True, blank=False
    )
    quantity = models.FloatField(
        default=0
    )  # Automatically Set // NOT EDITABLE BY ADMIN
    is_low = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["facility", "item"],
                condition=models.Q(deleted=False),
                name="unique_facility_item_summary",
            )
        ]


class FacilityInventoryMinQuantity(FacilityBaseModel, FacilityRelatedPermissionMixin):
    """
    Used to Specify the min value of an item for a particular item
    """

    facility = models.ForeignKey(
        "Facility", on_delete=models.CASCADE, null=False, blank=False
    )
    item = models.ForeignKey(
        FacilityInventoryItem, on_delete=models.SET_NULL, null=True, blank=False
    )
    min_quantity = models.FloatField(default=0, validators=[MinValueValidator(0.0)])

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["facility", "item"],
                condition=models.Q(deleted=False),
                name="unique_facility_item_min_quantity",
            )
        ]


class FacilityInventoryBurnRate(FacilityBaseModel, FacilityRelatedPermissionMixin):
    """
    Used to store the current burn rate of item.
    """

    facility = models.ForeignKey(
        "Facility", on_delete=models.CASCADE, null=False, blank=False
    )
    item = models.ForeignKey(
        FacilityInventoryItem, on_delete=models.SET_NULL, null=True, blank=False
    )
    burn_rate = models.FloatField(default=0)
    current_stock = models.FloatField(default=0)

    class Meta:
        unique_together = (
            "facility",
            "item",
        )
        indexes = [
            Index(
                fields=(
                    "facility",
                    "item",
                )
            )
        ]
