from rest_framework import serializers

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.models import FacilityCapacity


class FacilityCapacitySerializer(serializers.ModelSerializer):
    class Meta:
        model = FacilityCapacity
        exclude = TIMESTAMP_FIELDS + ('id', 'facility',)
