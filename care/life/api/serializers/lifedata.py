from rest_framework import serializers
from care.life.models import LifeData


class LifeDataSerializer(serializers.ModelSerializer):
    state_name = serializers.CharField(source="state.name")
    district_name = serializers.CharField(source="district.name")

    class Meta:
        model = LifeData
        fields = "__all__"
