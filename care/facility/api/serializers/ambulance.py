from django.db import transaction
from rest_framework import serializers

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.models import Ambulance, AmbulanceDriver


class AmbulanceDriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = AmbulanceDriver
        exclude = TIMESTAMP_FIELDS + ("ambulance",)


class AmbulanceSerializer(serializers.ModelSerializer):
    drivers = serializers.ListSerializer(child=AmbulanceDriverSerializer())

    class Meta:
        model = Ambulance
        exclude = TIMESTAMP_FIELDS

    def create(self, validated_data):
        with transaction.atomic():
            drivers = validated_data.pop("drivers", [])
            ambulance = super(AmbulanceSerializer, self).create(validated_data)
            for d in drivers:
                d["ambulance"] = ambulance
                AmbulanceDriverSerializer().create(d)
            return ambulance

    def update(self, instance, validated_data):
        validated_data.pop("drivers", [])
        ambulance = super(AmbulanceSerializer, self).update(instance, validated_data)
        return ambulance
