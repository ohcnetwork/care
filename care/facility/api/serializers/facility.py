from django.contrib.auth import get_user_model
from django.db import transaction
from drf_extra_fields.geo_fields import PointField
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from care.facility.api.serializers.facility_capacity import FacilityCapacitySerializer
from care.facility.models import FACILITY_TYPES, Facility
from care.users.models import DISTRICT_CHOICES
from config.serializers import ChoiceField

User = get_user_model()


class FacilitySerializer(serializers.ModelSerializer):
    """Serializer for facility.models.Facility."""

    district = ChoiceField(choices=DISTRICT_CHOICES)
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
            "district",
            "facility_type",
            "address",
            "location",
            "oxygen_capacity",
            "phone_number",
        ]


class FacilityUpsertSerializer(serializers.ModelSerializer):
    """
    Use only for listing and upserting - Upsert based on name and district uniqueness
    """

    capacity = serializers.ListSerializer(
        child=FacilityCapacitySerializer(), source="facilitycapacity_set"
    )
    location = PointField(required=False)

    class Meta:
        model = Facility
        fields = [
            "id",
            "name",
            "district",
            "facility_type",
            "address",
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
        capacities = validated_data.pop("facilitycapacity_set")
        facility = Facility.objects.filter(
            **{
                "name__iexact": validated_data["name"],
                "district": validated_data["district"],
            }
        ).first()

        user = self.context["user"]
        if not facility:
            validated_data["created_by"] = user
            facility = Facility.objects.create(**validated_data)
        else:
            if facility.created_by != user and not user.is_superuser:
                raise PermissionDenied(
                    f"{facility.name}, {DISTRICT_CHOICES[facility.district][1]} is owned by another user"
                )
            for k, v in validated_data.items():
                setattr(facility, k, v)
            facility.save()

        for ca in capacities:
            facility.facilitycapacity_set.update_or_create(
                room_type=ca["room_type"], defaults=ca
            )
        return facility

    def update(self, instance, validated_data):
        raise NotImplementedError()
