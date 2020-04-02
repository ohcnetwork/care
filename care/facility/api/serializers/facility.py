from django.contrib.auth import get_user_model
from drf_extra_fields.geo_fields import PointField
from rest_framework import serializers

from care.facility.api.serializers.facility_capacity import FacilityCapacitySerializer
from care.facility.models import FACILITY_TYPES, Facility, FacilityLocalGovtBody
from care.users.api.serializers.lsg import DistrictSerializer, LocalBodySerializer, StateSerializer
from config.serializers import ChoiceField

User = get_user_model()


class FacilityLocalGovtBodySerializer(serializers.ModelSerializer):
    local_body = LocalBodySerializer()
    district = DistrictSerializer()

    class Meta:
        model = FacilityLocalGovtBody
        fields = "__all__"


class FacilityBasicInfoSerializer(serializers.ModelSerializer):
    local_body_object = LocalBodySerializer(source="local_body", read_only=True)
    district_object = DistrictSerializer(source="district", read_only=True)
    state_object = StateSerializer(source="state", read_only=True)
    facility_type = serializers.SerializerMethodField()

    def get_facility_type(self, facility):
        return {"id": facility.facility_type, "name": FACILITY_TYPES[facility.facility_type - 1][1]}

    class Meta:
        model = Facility
        fields = (
            "id",
            "name",
            "local_body",
            "district",
            "state",
            "local_body_object",
            "district_object",
            "state_object",
            "facility_type",
        )


class FacilitySerializer(FacilityBasicInfoSerializer):
    """Serializer for facility.models.Facility."""

    facility_type = ChoiceField(choices=FACILITY_TYPES)
    # A valid location => {
    #     "latitude": 49.8782482189424,
    #     "longitude": 24.452545489
    # }
    location = PointField(required=False)

    class Meta:
        model = Facility
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
            "modified_date",
            "created_date",
        ]
        read_only_fields = ("modified_date", "created_date")

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class FacilityUpsertSerializer(serializers.ModelSerializer):
    """
    Use only for listing and upserting - Upsert based on name and district uniqueness
    """

    capacity = serializers.ListSerializer(child=FacilityCapacitySerializer(), source="facilitycapacity_set")
    location = PointField(required=False)
    district = serializers.IntegerField()

    class Meta:
        model = Facility
        fields = [
            "id",
            "name",
            "facility_type",
            "address",
            "district",
            "location",
            "oxygen_capacity",
            "phone_number",
            "capacity",
            "created_by",
        ]

    def validate_name(self, value):
        return str(value).strip().replace("  ", " ")

    def validate_phone_number(self, value):
        return str(value).strip().replace("  ", " ")

    def create(self, validated_data):
        raise NotImplementedError()

    def update(self, instance, validated_data):
        raise NotImplementedError()
