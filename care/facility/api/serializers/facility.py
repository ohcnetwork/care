import boto3
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import serializers

from care.facility.models import FACILITY_TYPES, Facility, FacilityLocalGovtBody
from care.facility.models.facility import FEATURE_CHOICES
from care.users.api.serializers.lsg import (
    DistrictSerializer,
    LocalBodySerializer,
    StateSerializer,
    WardSerializer,
)
from care.utils.csp import config as cs_provider
from config.serializers import ChoiceField
from config.validators import MiddlewareDomainAddressValidator

User = get_user_model()


class FacilityLocalGovtBodySerializer(serializers.ModelSerializer):
    local_body = LocalBodySerializer()
    district = DistrictSerializer()

    class Meta:
        model = FacilityLocalGovtBody
        fields = "__all__"


class FacilityBareMinimumSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)

    class Meta:
        model = Facility
        fields = (
            "id",
            "name",
        )


class FacilityBasicInfoSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)
    ward_object = WardSerializer(source="ward", read_only=True)
    local_body_object = LocalBodySerializer(source="local_body", read_only=True)
    district_object = DistrictSerializer(source="district", read_only=True)
    state_object = StateSerializer(source="state", read_only=True)
    facility_type = serializers.SerializerMethodField()
    read_cover_image_url = serializers.CharField(read_only=True)
    features = serializers.MultipleChoiceField(choices=FEATURE_CHOICES)

    def get_facility_type(self, facility):
        return {
            "id": facility.facility_type,
            "name": facility.get_facility_type_display(),
        }

    class Meta:
        model = Facility
        fields = (
            "id",
            "name",
            "local_body",
            "district",
            "state",
            "ward_object",
            "local_body_object",
            "district_object",
            "state_object",
            "facility_type",
            "read_cover_image_url",
            "features",
            "patient_count",
            "bed_count",
        )
        read_only_fields = (
            "patient_count",
            "bed_count",
        )


class FacilitySerializer(FacilityBasicInfoSerializer):
    """Serializer for facility.models.Facility."""

    facility_type = ChoiceField(choices=FACILITY_TYPES)
    # A valid location => {
    #     "latitude": 49.8782482189424,
    #     "longitude": 24.452545489
    # }
    read_cover_image_url = serializers.URLField(read_only=True)
    # location = PointField(required=False)
    features = serializers.MultipleChoiceField(choices=FEATURE_CHOICES)

    class Meta:
        model = Facility
        fields = [
            "id",
            "name",
            "ward",
            "local_body",
            "district",
            "state",
            "facility_type",
            "address",
            "longitude",
            "latitude",
            "features",
            "pincode",
            "oxygen_capacity",
            "phone_number",
            "ward_object",
            "local_body_object",
            "district_object",
            "state_object",
            "modified_date",
            "created_date",
            "kasp_empanelled",
            "middleware_address",
            "expected_oxygen_requirement",
            "type_b_cylinders",
            "type_c_cylinders",
            "type_d_cylinders",
            "expected_type_b_cylinders",
            "expected_type_c_cylinders",
            "expected_type_d_cylinders",
            "read_cover_image_url",
            "patient_count",
            "bed_count",
        ]
        read_only_fields = (
            "modified_date",
            "created_date",
            "patient_count",
            "bed_count",
        )

    def validate_middleware_address(self, value):
        value = value.strip()
        if not value:
            return value

        # Check if the address is valid
        MiddlewareDomainAddressValidator()(value)
        return value

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class FacilityImageUploadSerializer(serializers.ModelSerializer):
    cover_image = serializers.ImageField(required=True, write_only=True)
    read_cover_image_url = serializers.URLField(read_only=True)

    class Meta:
        model = Facility
        # Check DRYpermissions before updating
        fields = ("cover_image", "read_cover_image_url")

    def save(self, **kwargs):
        facility = self.instance
        image = self.validated_data["cover_image"]
        image_extension = image.name.rsplit(".", 1)[-1]
        s3 = boto3.client(
            "s3",
            **cs_provider.get_client_config(cs_provider.BucketType.FACILITY.value),
        )
        image_location = f"cover_images/{facility.external_id}_cover.{image_extension}"
        s3.put_object(
            Bucket=settings.FACILITY_S3_BUCKET,
            Key=image_location,
            Body=image.file,
        )
        facility.cover_image_url = image_location
        facility.save()
        return facility
