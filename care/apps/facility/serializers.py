from rest_framework import serializers as rest_serializer

from apps.facility import models as facility_models


class FacilitySerializer(rest_serializer.ModelSerializer):
    class Meta:
        model = facility_models.Facility
        fields = (
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


class FacilityUserSerializer(rest_serializer.ModelSerializer):
    class Meta:
        model = facility_models.FacilityUser
        fields = (
            "facility",
            "user",
            "created_by",
        )
