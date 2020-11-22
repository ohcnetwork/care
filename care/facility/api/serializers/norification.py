from django.db.models import F
from rest_framework import serializers

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.models import (
    ROOM_TYPES,
    FacilityInventoryItem,
    FacilityInventoryItemTag,
    FacilityInventoryLog,
    FacilityInventorySummary,
    FacilityInventoryUnit,
    FacilityInventoryUnitConverter,
    FacilityInventoryMinQuantity,
    models,
)

from config.serializers import ChoiceField
from care.facility.models.notification import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"
