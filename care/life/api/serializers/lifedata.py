from rest_framework import serializers

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.life.models import LifeData


class LifeDataSerializer(serializers.ModelSerializer):
    state = serializers.CharField(source="state.name")
    district = serializers.CharField(source="district.name")
    state_id = serializers.CharField(source="state.id")
    district_id = serializers.CharField(source="district.id")
    # data_source = serializers.CharField(source="created_job.file_url")
    data_name = serializers.CharField(source="created_job.name")

    class Meta:
        model = LifeData
        exclude = TIMESTAMP_FIELDS + ("id",)
