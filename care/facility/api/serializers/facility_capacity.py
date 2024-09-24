from rest_framework import serializers

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.models import FacilityCapacity, RoomType
from care.utils.serializers.fields import ChoiceField


class FacilityCapacitySerializer(serializers.ModelSerializer):
    room_type_text = ChoiceField(
        choices=RoomType.choices, read_only=True, source="room_type"
    )
    id = serializers.UUIDField(source="external_id", read_only=True)

    def validate(self, data):
        if (
            data.get("current_capacity")
            and data.get("total_capacity")
            and data["current_capacity"] > data["total_capacity"]
        ):
            raise serializers.ValidationError(
                {
                    "current_capacity": "Current capacity cannot be greater than total capacity."
                }
            )
        return data

    class Meta:
        model = FacilityCapacity
        read_only_fields = (
            "id",
            "room_type_text",
        )
        exclude = (
            "facility",
            "external_id",
            "created_date",
            "deleted",
        )


class FacilityCapacityHistorySerializer(serializers.ModelSerializer):
    def __init__(self, model, *args, **kwargs):
        self.Meta.model = model
        super().__init__()

    class Meta:
        exclude = (*TIMESTAMP_FIELDS, "facility")
