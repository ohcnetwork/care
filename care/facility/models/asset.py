import enum
import uuid

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import JSONField, Q

from care.facility.models import reverse_choices
from care.facility.models.facility import Facility
from care.facility.models.json_schema.asset import ASSET_META
from care.facility.models.mixins.permissions.facility import (
    FacilityRelatedPermissionMixin,
)
from care.users.models import User
from care.utils.assetintegration.asset_classes import AssetClasses
from care.utils.models.base import BaseModel
from care.utils.models.validators import JSONFieldSchemaValidator, PhoneNumberValidator


def get_random_asset_id():
    return str(uuid.uuid4())


class AvailabilityStatus(models.TextChoices):
    NOT_MONITORED = "Not Monitored"
    OPERATIONAL = "Operational"
    DOWN = "Down"
    UNDER_MAINTENANCE = "Under Maintenance"


class AssetLocation(BaseModel, FacilityRelatedPermissionMixin):
    """
    This model is also used to store rooms that the assets are in, Since these rooms are mapped to
    actual rooms in the hospital, Beds are also connected to this model to remove duplication of efforts
    """

    class RoomType(enum.Enum):
        OTHER = 1
        ICU = 10
        WARD = 20

    RoomTypeChoices = [(e.value, e.name) for e in RoomType]

    name = models.CharField(max_length=1024, blank=False, null=False)
    description = models.TextField(default="", null=True, blank=True)
    location_type = models.IntegerField(
        choices=RoomTypeChoices, default=RoomType.OTHER.value
    )
    facility = models.ForeignKey(
        Facility, on_delete=models.PROTECT, null=False, blank=False
    )

    middleware_address = models.CharField(
        null=True, blank=True, default=None, max_length=200
    )


class AssetType(enum.Enum):
    INTERNAL = 50
    EXTERNAL = 100


AssetTypeChoices = [(e.value, e.name) for e in AssetType]

AssetClassChoices = [(e.name, e.value._name) for e in AssetClasses]  # noqa: SLF001


class Status(enum.Enum):
    ACTIVE = 50
    TRANSFER_IN_PROGRESS = 100


StatusChoices = [(e.value, e.name) for e in Status]

REVERSE_ASSET_TYPE = reverse_choices(AssetTypeChoices)
REVERSE_STATUS = reverse_choices(StatusChoices)


class Asset(BaseModel):
    name = models.CharField(max_length=1024, blank=False, null=False)
    description = models.TextField(default="", null=True, blank=True)
    asset_type = models.IntegerField(
        choices=AssetTypeChoices, default=AssetType.INTERNAL.value
    )
    asset_class = models.CharField(
        choices=AssetClassChoices, default=None, null=True, blank=True, max_length=20
    )
    status = models.IntegerField(choices=StatusChoices, default=Status.ACTIVE.value)
    current_location = models.ForeignKey(
        AssetLocation, on_delete=models.PROTECT, null=False, blank=False
    )
    is_working = models.BooleanField(default=None, null=True, blank=True)
    not_working_reason = models.CharField(max_length=1024, blank=True, null=True)
    serial_number = models.CharField(max_length=1024, blank=True, null=True)
    warranty_details = models.TextField(null=True, blank=True, default="")  # Deprecated
    meta = JSONField(
        default=dict, blank=True, validators=[JSONFieldSchemaValidator(ASSET_META)]
    )
    # Vendor Details
    vendor_name = models.CharField(max_length=1024, blank=True, null=True)
    support_name = models.CharField(max_length=1024, blank=True, null=True)
    support_phone = models.CharField(
        max_length=15,
        validators=[PhoneNumberValidator(types=("mobile", "landline", "support"))],
        default="",
    )
    support_email = models.EmailField(blank=True, null=True)
    qr_code_id = models.CharField(max_length=1024, blank=True, default=None, null=True)
    manufacturer = models.CharField(max_length=1024, blank=True, null=True)
    warranty_amc_end_of_validity = models.DateField(default=None, null=True, blank=True)
    last_service = models.ForeignKey(
        "facility.AssetService",
        on_delete=models.SET_NULL,
        null=True,
        default=None,
        related_name="last_service",
    )

    CSV_MAPPING = {
        "name": "Name",
        "description": "Description",
        "asset_type": "Type",
        "asset_class": "Class",
        "status": "Status",
        "current_location__name": "Current Location Name",
        "is_working": "Working Status",
        "not_working_reason": "Not Working Reason",
        "serial_number": "Serial Number",
        "vendor_name": "Vendor Name",
        "support_name": "Support Name",
        "support_phone": "Support Phone Number",
        "support_email": "Support Email",
        "qr_code_id": "QR Code ID",
        "manufacturer": "Manufacturer",
        "warranty_amc_end_of_validity": "Warranty End Date",
        "last_service__serviced_on": "Last Service Date",
        "last_service__note": "Notes",
        "meta__local_ip_address": "Config - IP Address",
        "meta__camera_access_key": "Config: Camera Access Key",
    }

    CSV_MAKE_PRETTY = {
        "asset_type": (lambda x: REVERSE_ASSET_TYPE[x]),
        "status": (lambda x: REVERSE_STATUS[x]),
        "is_working": (lambda x: "WORKING" if x else "NOT WORKING"),
    }

    @property
    def resolved_middleware(self):
        if hostname := self.meta.get("middleware_hostname"):
            return {
                "hostname": hostname,
                "source": "asset",
            }
        if hostname := self.current_location.middleware_address:
            return {
                "hostname": hostname,
                "source": "location",
            }
        if hostname := self.current_location.facility.middleware_address:
            return {
                "hostname": hostname,
                "source": "facility",
            }
        return None

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["qr_code_id"],
                name="qr_code_unique_when_not_null",
                condition=Q(qr_code_id__isnull=False),
            ),
        ]

    def delete(self, *args, **kwargs):
        from care.facility.models.bed import AssetBed

        AssetBed.objects.filter(asset=self).update(deleted=True)
        super().delete(*args, **kwargs)

    @staticmethod
    def has_write_permission(request):
        if request.user.asset or request.user.user_type in User.READ_ONLY_TYPES:
            return False
        return (
            request.user.is_superuser
            or request.user.verified
            and request.user.user_type >= User.TYPE_VALUE_MAP["Staff"]
        )

    def has_object_write_permission(self, request):
        return self.has_write_permission(request)

    @staticmethod
    def has_read_permission(request):
        return request.user.is_superuser or request.user.verified

    def has_object_read_permission(self, request):
        return self.has_read_permission(request)

    def __str__(self):
        return self.name


class AvailabilityRecord(BaseModel):
    """
    Model to store the availability status of an object (Asset/AssetLocation for now) at a particular timestamp.

    Fields:
    - content_type: ContentType of the related model
    - object_external_id: UUIDField to store the external_id of the related model
    - content_object: To get the linked object
    - status: CharField with choices from AvailabilityStatus
    - timestamp: DateTimeField to store the timestamp of the availability record

    Note: A pair of (object_external_id, timestamp) is unique
    """

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_external_id = models.UUIDField()
    status = models.CharField(
        choices=AvailabilityStatus,
        default=AvailabilityStatus.NOT_MONITORED,
        max_length=20,
    )
    timestamp = models.DateTimeField(null=False, blank=False)

    class Meta:
        indexes = [
            models.Index(fields=["content_type", "object_external_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                name="object_external_id_timestamp",
                fields=["object_external_id", "timestamp"],
            )
        ]
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.content_type} ({self.object_external_id}) - {self.status} - {self.timestamp}"

    @property
    def content_object(self):
        model = self.content_type.model_class()
        return model.objects.get(external_id=self.object_external_id)


class UserDefaultAssetLocation(BaseModel):
    user = models.ForeignKey(User, on_delete=models.PROTECT, null=False, blank=False)
    location = models.ForeignKey(
        AssetLocation, on_delete=models.PROTECT, null=False, blank=False
    )


class FacilityDefaultAssetLocation(BaseModel):
    facility = models.ForeignKey(
        Facility, on_delete=models.PROTECT, null=False, blank=False
    )
    location = models.ForeignKey(
        AssetLocation, on_delete=models.PROTECT, null=False, blank=False
    )


class AssetTransaction(BaseModel):
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, null=False, blank=False)
    from_location = models.ForeignKey(
        AssetLocation,
        on_delete=models.PROTECT,
        related_name="from_location",
        null=False,
        blank=False,
    )
    to_location = models.ForeignKey(
        AssetLocation,
        on_delete=models.PROTECT,
        related_name="to_location",
        null=False,
        blank=False,
    )
    performed_by = models.ForeignKey(
        User, on_delete=models.PROTECT, null=False, blank=False
    )


class AssetService(BaseModel):
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, null=False, blank=False)

    serviced_on = models.DateField(default=None, null=True, blank=False)
    note = models.TextField(default="", null=True, blank=True)

    @property
    def edit_history(self):
        return self.edits.order_by("-edited_on")


class AssetServiceEdit(models.Model):
    asset_service = models.ForeignKey(
        AssetService,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="edits",
    )
    edited_on = models.DateTimeField(auto_now_add=True)
    edited_by = models.ForeignKey(
        User, on_delete=models.PROTECT, null=False, blank=False
    )

    serviced_on = models.DateField()
    note = models.TextField()

    class Meta:
        ordering = ["-edited_on"]

    def __str__(self):
        return f"{self.asset_service.asset.name} - {self.serviced_on}"
