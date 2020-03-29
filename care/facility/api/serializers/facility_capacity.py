from rest_framework import serializers

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.models import ROOM_TYPES, FacilityCapacity
from config.serializers import ChoiceField


class FacilityCapacitySerializer(serializers.ModelSerializer):
    room_type_text = ChoiceField(choices=ROOM_TYPES, read_only=True, source="room_type")

    class Meta:
        model = FacilityCapacity
        read_only_fields = (
            "id",
            "room_type_text",
        )
        exclude = TIMESTAMP_FIELDS + ("facility",)


class FacilityCapacityHistorySerializer(serializers.ModelSerializer):
    def __init__(self, model, *args, **kwargs):
        self.Meta.model = model
        super().__init__()

    class Meta:
        exclude = TIMESTAMP_FIELDS + ("facility",)
