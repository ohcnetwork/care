from rest_framework import serializers as rest_serializers

from apps.facility import models as facility_models


class FacilitySerializer(rest_serializers.ModelSerializer):
    class Meta:
        model = facility_models.Facility
        fields = (
            "id",
            "name",
            "facility_code",
            "facility_type",
            "location",
            "address",
            "local_body",
            "district",
            "state",
            "phone_number",
            "corona_testing",
            "created_by",
            "owned_by",
            "total_patient",
            "positive_patient",
            "negative_patient",
        )


class FacilityUserSerializer(rest_serializers.ModelSerializer):
    class Meta:
        model = facility_models.FacilityUser
        fields = (
            "facility",
            "user",
            "created_by",
        )


class FacilityTypeSerializer(rest_serializers.ModelSerializer):
    class Meta:
        model = facility_models.FacilityType
        fields = (
            "id",
            "name",
        )


class InventorySerializer(rest_serializers.ModelSerializer):
    class Meta:
        model = facility_models.Inventory
        fields = (
            "facility",
            "item",
            "required_quantity",
            "current_quantity",
            "created_by",
        )
