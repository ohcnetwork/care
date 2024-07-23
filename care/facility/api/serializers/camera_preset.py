from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from care.facility.api.serializers.bed import AssetBedSerializer
from care.facility.models import CameraPreset
from care.users.api.serializers.user import UserBaseMinimumSerializer


class CameraPresetSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)
    created_by = UserBaseMinimumSerializer(read_only=True)
    updated_by = UserBaseMinimumSerializer(read_only=True)
    asset_bed = AssetBedSerializer(read_only=True)

    class Meta:
        model = CameraPreset
        exclude = (
            "external_id",
            "deleted",
        )
        read_only_fields = (
            "created_date",
            "modified_date",
            "is_migrated",
            "created_by",
            "updated_by",
        )

    def validate(self, attrs):
        validated_data = super().validate(attrs)

        asset_bed = (
            self.instance.asset_bed if self.instance else self.context["asset_bed"]
        )
        position = validated_data.get(
            "position", self.instance and self.instance.position
        )
        boundary = validated_data.get(
            "boundary", self.instance and self.instance.boundary
        )

        if not self.instance:
            # one of position or boundary only must be present
            if not (validated_data.get("position") or validated_data.get("boundary")):
                raise ValidationError("Either position or boundary must be specified")

            # single boundary preset for an asset_bed
            if boundary and CameraPreset.objects.filter(asset_bed=asset_bed).exists():
                raise ValidationError(
                    "Only one boundary preset can exist for an asset_bed"
                )
        # one of position or boundary only must be present
        if position and boundary:
            raise ValidationError("Cannot have both position and a boundary.")

        return validated_data

    def create(self, validated_data):
        validated_data["asset_bed"] = self.context["asset_bed"]
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data["updated_by"] = self.context["request"].user
        return super().create(validated_data)
