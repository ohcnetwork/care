import enum
from datetime import datetime

from django.core.cache import cache
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import (
    CharField,
    JSONField,
    ModelSerializer,
    Serializer,
    UUIDField,
)
from rest_framework.validators import UniqueValidator

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.api.serializers.facility import FacilityBareMinimumSerializer
from care.facility.models.asset import (
    Asset,
    AssetLocation,
    AssetTransaction,
    UserDefaultAssetLocation,
)
from care.users.api.serializers.user import UserBaseMinimumSerializer
from care.utils.assetintegration.hl7monitor import HL7MonitorAsset
from care.utils.assetintegration.onvif import OnvifAsset
from care.utils.assetintegration.ventilator import VentilatorAsset
from care.utils.queryset.facility import get_facility_queryset
from config.serializers import ChoiceField


class AssetLocationSerializer(ModelSerializer):
    facility = FacilityBareMinimumSerializer(read_only=True)
    id = UUIDField(source="external_id", read_only=True)

    def validate(self, data):
        facility = self.context["facility"]
        if "name" in data:
            name = data["name"]
            asset_location_id = self.instance.id if self.instance else None
            if (
                AssetLocation.objects.filter(name=name, facility=facility)
                .exclude(id=asset_location_id)
                .exists()
            ):
                raise ValidationError(
                    {
                        "name": "Asset location with this name and facility already exists."
                    }
                )
        return data

    class Meta:
        model = AssetLocation
        exclude = (
            "deleted",
            "external_id",
        )
        read_only_fields = TIMESTAMP_FIELDS


class AssetSerializer(ModelSerializer):
    id = UUIDField(source="external_id", read_only=True)
    status = ChoiceField(choices=Asset.StatusChoices, read_only=True)
    asset_type = ChoiceField(choices=Asset.AssetTypeChoices)
    location_object = AssetLocationSerializer(source="current_location", read_only=True)
    location = UUIDField(write_only=True, required=True)

    class Meta:
        model = Asset
        exclude = ("deleted", "external_id", "current_location")
        read_only_fields = TIMESTAMP_FIELDS

    def validate_qr_code_id(self, value):
        value = value or None  # treat empty string as null
        UniqueValidator(
            queryset=Asset.objects.filter(qr_code_id__isnull=False),
            message="QR code already assigned",
        )(value, self.fields.get("qr_code_id"))
        return value

    def validate(self, attrs):
        user = self.context["request"].user
        if "location" in attrs:
            location = get_object_or_404(
                AssetLocation.objects.filter(external_id=attrs["location"])
            )

            facilities = get_facility_queryset(user)
            if not facilities.filter(id=location.facility.id).exists():
                raise PermissionError()
            del attrs["location"]
            attrs["current_location"] = location

        # validate that warraty date is not in the past
        if "warranty_amc_end_of_validity" in attrs:
            if (
                attrs["warranty_amc_end_of_validity"]
                and attrs["warranty_amc_end_of_validity"] < datetime.now().date()
            ):
                raise ValidationError(
                    "Warranty/AMC end of validity cannot be in the past"
                )

        # validate that last serviced date is not in the future
        if "last_serviced_on" in attrs and attrs["last_serviced_on"]:
            if attrs["last_serviced_on"] > datetime.now().date():
                raise ValidationError("Last serviced on cannot be in the future")

        # only allow setting asset class on creation (or updation if asset class is not set)
        if (
            attrs.get("asset_class")
            and self.instance
            and self.instance.asset_class
            and self.instance.asset_class != attrs["asset_class"]
        ):
            raise ValidationError({"asset_class": "Cannot change asset class"})

        return super().validate(attrs)

    def update(self, instance, validated_data):
        user = self.context["request"].user

        with transaction.atomic():
            if (
                "current_location" in validated_data
                and instance.current_location != validated_data["current_location"]
            ):
                if (
                    instance.current_location.facility.id
                    != validated_data["current_location"].facility.id
                ):
                    raise ValidationError(
                        {"location": "Interfacility transfer is not allowed here"}
                    )
                AssetTransaction(
                    from_location=instance.current_location,
                    to_location=validated_data["current_location"],
                    asset=instance,
                    performed_by=user,
                ).save()
            updated_instance = super().update(instance, validated_data)
            cache.delete(f"asset:{instance.external_id}")
        return updated_instance


class AssetBareMinimumSerializer(ModelSerializer):
    id = UUIDField(source="external_id", read_only=True)

    class Meta:
        model = Asset
        fields = ("name", "id")


class AssetTransactionSerializer(ModelSerializer):
    id = UUIDField(source="external_id", read_only=True)
    asset = AssetBareMinimumSerializer(read_only=True)
    from_location = AssetLocationSerializer(read_only=True)
    to_location = AssetLocationSerializer(read_only=True)
    performed_by = UserBaseMinimumSerializer(read_only=True)

    class Meta:
        model = AssetTransaction
        exclude = ("deleted", "external_id")


class UserDefaultAssetLocationSerializer(ModelSerializer):
    location_object = AssetLocationSerializer(source="location", read_only=True)

    class Meta:
        model = UserDefaultAssetLocation
        exclude = ("deleted", "external_id", "location", "user", "id")


class AssetActionSerializer(Serializer):
    def actionChoices():
        actions: list[enum.Enum] = [
            OnvifAsset.OnvifActions,
            HL7MonitorAsset.HL7MonitorActions,
            VentilatorAsset.VentilatorActions,
        ]
        choices = []
        for action in actions:
            choices += [(e.value, e.name) for e in action]
        return choices

    type = ChoiceField(
        choices=actionChoices(),
        required=True,
    )
    data = JSONField(required=False)


class DummyAssetOperateSerializer(Serializer):
    action = AssetActionSerializer(required=True)


class DummyAssetOperateResponseSerializer(Serializer):
    message = CharField(required=True)
    result = JSONField(required=False)
