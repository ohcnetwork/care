from rest_framework import serializers
from care.life.models import LifeData


class LifeDataSerializer(serializers.ModelSerializer):
    state_name = serializers.CharField(source="state.name")
    district_name = serializers.CharField(source="district.name")
    data_source = serializers.CharField(source="created_job.file_url")
    data_name = serializers.CharField(source="created_job.name")

    class Meta:
        model = LifeData
        exclude = ("id",)
