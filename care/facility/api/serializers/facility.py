import boto3
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import serializers

from care.facility.models import FACILITY_TYPES, Facility, FacilityLocalGovtBody
from care.facility.models.bed import Bed
from care.facility.models.facility import FEATURE_CHOICES, FacilityHubSpoke
from care.facility.models.patient import PatientRegistration
from care.users.api.serializers.lsg import (
    DistrictSerializer,
    LocalBodySerializer,
    StateSerializer,
    WardSerializer,
)
from care.utils.csp.config import BucketType, get_client_config
from care.utils.serializer.external_id_field import ExternalIdSerializerField
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
    features = serializers.ListField(
        child=serializers.ChoiceField(choices=FEATURE_CHOICES),
        required=False,
    )
    patient_count = serializers.SerializerMethodField()
    bed_count = serializers.SerializerMethodField()

    def get_bed_count(self, facility):
        return Bed.objects.filter(facility=facility).count()

    def get_patient_count(self, facility):
        return PatientRegistration.objects.filter(
            facility=facility, is_active=True
        ).count()

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


class FacilitySerializer(FacilityBasicInfoSerializer):
    """Serializer for facility.models.Facility."""

    facility_type = ChoiceField(choices=FACILITY_TYPES)
    # A valid location => {
    #     "latitude": 49.8782482189424,
    #     "longitude": 24.452545489
    # }
    read_cover_image_url = serializers.URLField(read_only=True)
    # location = PointField(required=False)
    features = serializers.ListField(
        child=serializers.ChoiceField(choices=FEATURE_CHOICES),
        required=False,
    )
    bed_count = serializers.SerializerMethodField()

    facility_flags = serializers.SerializerMethodField()

    def get_facility_flags(self, facility):
        return facility.get_facility_flags()

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
            "facility_flags",
        ]
        read_only_fields = ("modified_date", "created_date")

    def validate_middleware_address(self, value):
        if not value:
            raise serializers.ValidationError("Middleware Address is required")
        value = value.strip()
        if not value:
            return value

        # Check if the address is valid
        MiddlewareDomainAddressValidator()(value)
        return value

    def validate_features(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError(
                "Features should not contain duplicate values."
            )
        return value

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class FacilitySpokeSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)
    spoke = ExternalIdSerializerField(
        queryset=Facility.objects.all(), required=True, write_only=True
    )
    hub_object = FacilityBasicInfoSerializer(read_only=True, source="hub")
    spoke_object = FacilityBasicInfoSerializer(read_only=True, source="spoke")

    class Meta:
        model = FacilityHubSpoke
        fields = (
            "id",
            "spoke",
            "hub_object",
            "spoke_object",
            "relationship",
            "created_date",
            "modified_date",
        )
        read_only_fields = (
            "id",
            "spoke_object",
            "hub_object",
            "created_date",
            "modified_date",
        )

    def validate(self, data):
        data["hub"] = self.context["facility"]
        return data

    def validate_spoke(self, spoke: Facility):
        hub: Facility = self.context["facility"]
        user = self.context["request"].user

        if hub == spoke:
            raise serializers.ValidationError("Cannot set a facility as it's own spoke")

        if not (
            user.is_superuser
            or (
                user.user_type <= User.TYPE_VALUE_MAP["LocalBodyAdmin"]
                and spoke.state == user.state
                and spoke.district == user.district
                and spoke.local_body == user.local_body
            )
            or (
                user.user_type > User.TYPE_VALUE_MAP["LocalBodyAdmin"]
                and user.user_type <= User.TYPE_VALUE_MAP["DistrictAdmin"]
                and spoke.state == user.state
                and spoke.district == user.district
            )
            or (
                user.user_type > User.TYPE_VALUE_MAP["DistrictAdmin"]
                and user.user_type <= User.TYPE_VALUE_MAP["StateAdmin"]
                and spoke.state == user.state
            )
        ):
            raise serializers.ValidationError(
                "You do not have permission to set this spoke"
            )

        if FacilityHubSpoke.objects.filter(
            Q(hub=hub, spoke=spoke) | Q(hub=spoke, spoke=hub)
        ).first():
            raise serializers.ValidationError("Facility is already a spoke/hub")

        return spoke


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
        config, bucket_name = get_client_config(BucketType.FACILITY)
        s3 = boto3.client("s3", **config)
        image_location = f"cover_images/{facility.external_id}_cover.{image_extension}"
        boto_params = {
            "Bucket": bucket_name,
            "Key": image_location,
            "Body": image.file,
        }
        if settings.BUCKET_HAS_FINE_ACL:
            boto_params["ACL"] = "public-read"
        s3.put_object(**boto_params)
        facility.cover_image_url = image_location
        facility.save()
        return facility
