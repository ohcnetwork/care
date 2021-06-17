from care.facility.models.asset import AssetLocation
from rest_framework.serializers import ModelSerializer, UUIDField

from care.facility.api.serializers.facility import FacilityBareMinimumSerializer

from care.facility.api.serializers import TIMESTAMP_FIELDS


class AssetLocationSerializer(ModelSerializer):
    facility = FacilityBareMinimumSerializer(read_only=True)
    id = UUIDField(source="external_id", read_only=True)

    class Meta:
        model = AssetLocation
        exclude = ("deleted", "external_id")
        read_only_fields = TIMESTAMP_FIELDS
