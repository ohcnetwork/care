from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.models.ambulance import Ambulance, AmbulanceDriver
from care.users.api.serializers.lsg import DistrictSerializer


class AmbulanceDriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = AmbulanceDriver
        exclude = TIMESTAMP_FIELDS + ("ambulance",)


class AmbulanceSerializer(serializers.ModelSerializer):
    drivers = serializers.ListSerializer(child=AmbulanceDriverSerializer())

    primary_district_object = DistrictSerializer(read_only=True, source="primary_district")
    secondary_district_object = DistrictSerializer(read_only=True, source="secondary_district")
    third_district_object = DistrictSerializer(read_only=True, source="third_district")

    class Meta:
        model = Ambulance
        read_only_fields = (
            "primary_district_object",
            "secondary_district_object",
            "third_district_object",
        )
        exclude = ("created_by",)

    def validate(self, obj):
        validated = super().validate(obj)
        if not validated.get("price_per_km") and not validated.get("has_free_service"):
            raise ValidationError("The ambulance must provide a price or be marked as free")
        return validated

    def create(self, validated_data):
        with transaction.atomic():
            drivers = validated_data.pop("drivers", [])
            validated_data.pop("created_by", None)

            ambulance = super(AmbulanceSerializer, self).create(validated_data)

            for d in drivers:
                d["ambulance"] = ambulance
                AmbulanceDriverSerializer().create(d)
            return ambulance

    def update(self, instance, validated_data):
        validated_data.pop("drivers", [])
        ambulance = super(AmbulanceSerializer, self).update(instance, validated_data)
        return ambulance
