from django.db import transaction
from rest_framework import serializers

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.models import Ambulance, AmbulanceDriver
from care.users.api.serializers.lsg import DistrictSerializer


class AmbulanceDriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = AmbulanceDriver
        exclude = TIMESTAMP_FIELDS + ("ambulance",)


class AmbulanceSerializer(serializers.ModelSerializer):
    drivers = serializers.ListSerializer(child=AmbulanceDriverSerializer())

    class Meta:
        model = Ambulance
        exclude = TIMESTAMP_FIELDS

    def to_representation(self, instance):
        data = super(AmbulanceSerializer, self).to_representation(instance)
        data["primary_district"] = (
            DistrictSerializer().to_representation(instance.primary_district) if instance.primary_district else None
        )
        data["secondary_district"] = (
            DistrictSerializer().to_representation(instance.secondary_district) if instance.secondary_district else None
        )
        data["third_district"] = (
            DistrictSerializer().to_representation(instance.third_district) if instance.third_district else None
        )
        return data

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
