from django.contrib.auth import get_user_model
from django.db import transaction
from drf_extra_fields.geo_fields import PointField
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from care.facility.api.serializers.facility_capacity import FacilityCapacitySerializer
from care.facility.models import (
    FACILITY_TYPES,
    District,
    Facility,
    FacilityLocalGovtBody,
    LocalBody,
)
from care.users.api.serializers.lsg import DistrictSerializer, LocalBodySerializer
from config.serializers import ChoiceField

User = get_user_model()


class FacilityLocalGovtBodySerializer(serializers.ModelSerializer):
    local_body = LocalBodySerializer()
    district = DistrictSerializer()

    class Meta:
        model = FacilityLocalGovtBody
        fields = "__all__"


class FacilitySerializer(serializers.ModelSerializer):
    """Serializer for facility.models.Facility."""

    facility_type = ChoiceField(choices=FACILITY_TYPES)
    # A valid location => {
    #     "latitude": 49.8782482189424,
    #     "longitude": 24.452545489
    # }
    location = PointField(required=False)
    local_body = serializers.IntegerField(required=False)
    local_govt_body = FacilityLocalGovtBodySerializer(read_only=True)

    class Meta:
        model = Facility
        fields = [
            "id",
            "name",
            "local_body",
            "local_govt_body",
            "district",
            "facility_type",
            "address",
            "location",
            "oxygen_capacity",
            "phone_number",
        ]

    def validate_local_body(self, value):
        if value is not None:
            try:
                value = LocalBody.objects.get(pk=value)
            except LocalBody.DoesNotExist:
                raise serializers.ValidationError({"local_body": "Not found"})
        return value

    def validate_district(self, value):
        try:
            District.objects.get(pk=value)
        except District.DoesNotExist:
            raise serializers.ValidationError({"district": "Not found"})
        return value

    def create(self, validated_data):
        with transaction.atomic():
            local_body = validated_data.pop("local_body", None)
            facility = super(FacilitySerializer, self).create(validated_data)
            if facility.local_govt_body is None:
                facility.local_govt_body = FacilityLocalGovtBody(facility=facility)
            facility.local_govt_body.local_body = local_body
            facility.local_govt_body.district_id = validated_data["district"]
            facility.local_govt_body.save()
            return facility

    def update(self, instance, validated_data):
        with transaction.atomic():
            local_body = validated_data.pop("local_body", None)
            facility = super(FacilitySerializer, self).update(instance, validated_data)
            if facility.local_govt_body is None:
                facility.local_govt_body = FacilityLocalGovtBody(facility=facility)
            facility.local_govt_body.local_body = local_body
            facility.local_govt_body.district_id = validated_data["district"]
            facility.local_govt_body.save()
            return facility


class FacilityUpsertSerializer(serializers.ModelSerializer):
    """
    Use only for listing and upserting - Upsert based on name and district uniqueness
    """

    capacity = serializers.ListSerializer(child=FacilityCapacitySerializer(), source="facilitycapacity_set")
    location = PointField(required=False)
    local_body = serializers.IntegerField(required=False)

    class Meta:
        model = Facility
        fields = [
            "id",
            "name",
            "district",
            "local_body",
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

    def validate_local_body(self, value):
        if value is not None:
            try:
                value = LocalBody.objects.get(id=value)
            except LocalBody.DoesNotExist:
                raise serializers.ValidationError({"local_body": "Not found"})
        return value

    def validate_district(self, value):
        try:
            District.objects.get(pk=value)
        except District.DoesNotExist:
            raise serializers.ValidationError({"district": "Not found"})
        return value

    def create(self, validated_data):
        capacities = validated_data.pop("facilitycapacity_set")
        local_body = validated_data.pop("local_body", None)
        facility = Facility.objects.filter(
            **{"name__iexact": validated_data["name"], "district": validated_data["district"],}
        ).first()

        user = self.context["user"]
        if not facility:
            validated_data["created_by"] = user
            facility = Facility.objects.create(**validated_data)
        else:
            if facility.created_by != user and not user.is_superuser:
                raise PermissionDenied(f"{facility} is owned by another user")

            for k, v in validated_data.items():
                setattr(facility, k, v)
            facility.save()

        if facility.local_govt_body is None:
            facility.local_govt_body = FacilityLocalGovtBody(facility=facility)

        facility.local_govt_body.local_body = local_body
        facility.local_govt_body.district_id = validated_data["district"]
        facility.local_govt_body.save()

        for ca in capacities:
            facility.facilitycapacity_set.update_or_create(room_type=ca["room_type"], defaults=ca)
        return facility

    def update(self, instance, validated_data):
        raise NotImplementedError()
