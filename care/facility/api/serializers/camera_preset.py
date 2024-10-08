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
        return (
            self.instance.asset_bed if self.instance else self.context.get("asset_bed")
        )

    def validate_name(self, value):
        if CameraPreset.objects.filter(
            asset_bed__bed_id=self.get_asset_bed_obj().bed_id, name=value
        ).exists():
            msg = "Name should be unique. Another preset related to this bed already uses the same name."
            raise ValidationError(msg)
        return value

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        validated_data["asset_bed"] = self.get_asset_bed_obj()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data["updated_by"] = self.context["request"].user
        return super().update(instance, validated_data)
