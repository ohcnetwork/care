from rest_framework import serializers

from care.abdm.models import HealthFacility


class HealthFacilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthFacility
        exclude = ("deleted",)
