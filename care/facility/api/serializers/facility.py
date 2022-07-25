from distutils import extension
import boto3

from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework import serializers

from care.facility.api.serializers.facility_capacity import FacilityCapacitySerializer
from care.facility.models import FACILITY_TYPES, Facility, FacilityLocalGovtBody
from care.facility.models.facility import FEATURE_CHOICES
from care.facility.models.patient_base import reverse_choices
from care.users.api.serializers.lsg import DistrictSerializer, LocalBodySerializer, StateSerializer, WardSerializer
from config.serializers import ChoiceField
from care.utils.csp import config as cs_provider

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
        return {"id": facility.facility_type, "name": facility.get_facility_type_display()}

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
        )


class FacilitySerializer(FacilityBasicInfoSerializer):
    """Serializer for facility.models.Facility."""

    facility_type = ChoiceField(choices=FACILITY_TYPES)
    # A valid location => {
    #     "latitude": 49.8782482189424,
    #     "longitude": 24.452545489
    # }
    read_cover_image_url = serializers.CharField(read_only=True)
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
            "expected_oxygen_requirement",
            "type_b_cylinders",
            "type_c_cylinders",
            "type_d_cylinders",
            "expected_type_b_cylinders",
            "expected_type_c_cylinders",
            "expected_type_d_cylinders",
            "read_cover_image_url",
        ]
        read_only_fields = ("modified_date", "created_date")

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class FacilityImageUploadSerializer(serializers.ModelSerializer):
    cover_image = serializers.ImageField(required=True, write_only=True)

    class Meta:
        model = Facility
        fields = ("cover_image",)

    def save(self, **kwargs):
        facility = self.instance
        image = self.validated_data["cover_image"]
        image_extension = image.name.split(".")[-1]
        s3 = boto3.client(
            "s3",
            **cs_provider.get_client_config(cs_provider.BucketType.FACILITY.value)
        )
        upload_response = s3.put_object(
            Bucket=settings.FACILITY_S3_BUCKET,
            Key=f"cover_images/{facility.external_id}_cover.{image_extension}",
            Body=image.file,
        )
        print(upload_response['ResponseMetadata']['HTTPHeaders']['location'])
        facility.cover_image_url = f"cover_images/{facility.external_id}_cover.{image_extension}"
        facility.save()
        return facility
