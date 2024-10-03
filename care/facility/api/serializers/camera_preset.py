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

    def get_asset_bed_obj(self):
        return self.instance.asset_bed if self.instance else self.context["asset_bed"]

    def validate_name(self, value):
        presets_of_related_bed = (
            CameraPreset.objects.filter(
                asset_bed__bed_id=self.get_asset_bed_obj().bed_id
            )
            .only("name")
            .values_list("name")
        )
        if value in [x[0] for x in presets_of_related_bed]:
            msg = "Name should be unique. Another preset related to this bed already uses the same name."
            raise ValidationError(msg)
        return value

    def validate(self, attrs):
        validated_data = super().validate(attrs)

        asset_bed = self.get_asset_bed_obj()
        position = validated_data.get(
            "position", self.instance and self.instance.position
        )
        boundary = validated_data.get(
            "boundary", self.instance and self.instance.boundary
        )

        if not self.instance:
            # one of position or boundary only must be present
            if not (validated_data.get("position") or validated_data.get("boundary")):
                msg = "Either position or boundary must be specified"
                raise ValidationError(msg)

            # single boundary preset for an asset_bed
            if boundary and CameraPreset.objects.filter(asset_bed=asset_bed).exists():
                msg = "Only one boundary preset can exist for an asset_bed"
                raise ValidationError(msg)
        # one of position or boundary only must be present
        if position and boundary:
            msg = "Cannot have both position and a boundary."
            raise ValidationError(msg)

        validated_data["asset_bed"] = self.get_asset_bed_obj()
        return validated_data

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data["updated_by"] = self.context["request"].user
        return super().update(instance, validated_data)
