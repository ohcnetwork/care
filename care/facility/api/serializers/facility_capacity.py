from rest_framework import serializers

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.models import FacilityCapacity


class FacilityCapacitySerializer(serializers.ModelSerializer):
    class Meta:
        model = FacilityCapacity
        read_only_fields = ("id",)
        exclude = TIMESTAMP_FIELDS + ("facility",)


class FacilityCapacityHistorySerializer(serializers.ModelSerializer):
    def __init__(self, model, *args, **kwargs):
        self.Meta.model = model
        super().__init__()

    class Meta:
        exclude = TIMESTAMP_FIELDS + ("facility",)
