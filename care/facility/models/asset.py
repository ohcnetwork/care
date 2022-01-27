import enum

from django.contrib.postgres.fields.jsonb import JSONField
from django.db import models

from care.facility.models.facility import Facility
from care.users.models import User, phone_number_regex
from care.utils.models.base import BaseModel


class AssetLocation(BaseModel):
    """
    This model is also used to store rooms that the assets are in, Since these rooms are mapped to
    actual rooms in the hospital, Beds are also connected to this model to remove duplication of efforts
    """

    class RoomType(enum.Enum):
        OTHER = 1
        ICU = 10

    RoomTypeChoices = [(e.value, e.name) for e in RoomType]

    name = models.CharField(max_length=1024, blank=False, null=False)
    description = models.TextField(default="", null=True, blank=True)
    location_type = models.IntegerField(choices=RoomTypeChoices, default=RoomType.OTHER.value)
    facility = models.ForeignKey(Facility, on_delete=models.PROTECT, null=False, blank=False)


class Asset(BaseModel):
    class AssetType(enum.Enum):
        INTERNAL = 50
        EXTERNAL = 100

    AssetTypeChoices = [(e.value, e.name) for e in AssetType]

    class Status(enum.Enum):
        ACTIVE = 50
        TRANSFER_IN_PROGRESS = 100

    StatusChoices = [(e.value, e.name) for e in Status]

    name = models.CharField(max_length=1024, blank=False, null=False)
    description = models.TextField(default="", null=True, blank=True)
    asset_type = models.IntegerField(choices=AssetTypeChoices, default=AssetType.INTERNAL.value)
    status = models.IntegerField(choices=StatusChoices, default=Status.ACTIVE.value)
    current_location = models.ForeignKey(AssetLocation, on_delete=models.PROTECT, null=False, blank=False)
    is_working = models.BooleanField(default=None, null=True, blank=True)
    not_working_reason = models.CharField(max_length=1024, blank=True, null=True)
    serial_number = models.CharField(max_length=1024, blank=True, null=True)
    warranty_details = models.TextField(null=True, blank=True, default="")
    meta = JSONField(default=dict)
    # Vendor Details
    vendor_name = models.CharField(max_length=1024, blank=True, null=True)
    support_name = models.CharField(max_length=1024, blank=True, null=True)
    support_phone = models.CharField(max_length=14, validators=[phone_number_regex], default="")
    support_email = models.EmailField(blank=True, null=True)


class UserDefaultAssetLocation(BaseModel):
    user = models.ForeignKey(User, on_delete=models.PROTECT, null=False, blank=False)
    location = models.ForeignKey(AssetLocation, on_delete=models.PROTECT, null=False, blank=False)


class FacilityDefaultAssetLocation(BaseModel):
    facility = models.ForeignKey(Facility, on_delete=models.PROTECT, null=False, blank=False)
    location = models.ForeignKey(AssetLocation, on_delete=models.PROTECT, null=False, blank=False)


class AssetTransaction(BaseModel):
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, null=False, blank=False)
    from_location = models.ForeignKey(
        AssetLocation, on_delete=models.PROTECT, related_name="from_location", null=False, blank=False
    )
    to_location = models.ForeignKey(
        AssetLocation, on_delete=models.PROTECT, related_name="to_location", null=False, blank=False
    )
    performed_by = models.ForeignKey(User, on_delete=models.PROTECT, null=False, blank=False)
