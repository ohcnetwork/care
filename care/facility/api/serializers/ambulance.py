from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.models import Ambulance, AmbulanceDriver
from care.users.api.serializers.lsg import DistrictSerializer


class AmbulanceDriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = AmbulanceDriver
        exclude = TIMESTAMP_FIELDS + ("ambulance",)


class AmbulanceSerializer(serializers.ModelSerializer):
    drivers = serializers.ListSerializer(child=AmbulanceDriverSerializer())

    primary_district = DistrictSerializer(read_only=True)
    secondary_district = DistrictSerializer(read_only=True)
    third_district = DistrictSerializer(read_only=True)

    class Meta:
        model = Ambulance
        fields = [
            "id",
            "name",
            "local_body",
            "district",
            "state",
            "facility_type",
            "address",
            "location",
            "oxygen_capacity",
            "phone_number",
            "local_body_object",
            "district_object",
            "state_object",
        ]

    # def to_representation(self, instance):
    #     data = super(AmbulanceSerializer, self).to_representation(instance)
    #     data["primary_district"] = (
    #         DistrictSerializer().to_representation(instance.primary_district_obj)
    #         if instance.primary_district_obj
    #         else None
    #     )
    #     data["secondary_district"] = (
    #         DistrictSerializer().to_representation(instance.secondary_district_obj)
    #         if instance.secondary_district_obj
    #         else None
    #     )
    #     data["third_district"] = (
    #         DistrictSerializer().to_representation(instance.third_district_obj) if instance.third_district_obj else None
    #     )
    #     return data

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
