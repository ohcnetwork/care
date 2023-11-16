from datetime import datetime

from django.core.cache import cache
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from rest_framework import serializers
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
    AssetAvailabilityRecord,
    AssetLocation,
    AssetService,
    AssetServiceEdit,
    AssetTransaction,
    AssetTypeChoices,
    StatusChoices,
    UserDefaultAssetLocation,
)
from care.users.api.serializers.user import UserBaseMinimumSerializer
from care.utils.assetintegration.hl7monitor import HL7MonitorAsset
from care.utils.assetintegration.onvif import OnvifAsset
from care.utils.assetintegration.ventilator import VentilatorAsset
from care.utils.queryset.facility import get_facility_queryset
from config.serializers import ChoiceField
from config.validators import MiddlewareDomainAddressValidator


class AssetLocationSerializer(ModelSerializer):
    facility = FacilityBareMinimumSerializer(read_only=True)
    id = UUIDField(source="external_id", read_only=True)

    def validate_middleware_address(self, value):
        value = (value or "").strip()
        if not value:
            return value

        # Check if the address is valid
        MiddlewareDomainAddressValidator()(value)
        return value

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


class AssetBareMinimumSerializer(ModelSerializer):
    id = UUIDField(source="external_id", read_only=True)

    class Meta:
        model = Asset
        fields = ("name", "id")


class AssetServiceEditSerializer(ModelSerializer):
    id = UUIDField(source="asset_service.external_id", read_only=True)
    edited_by = UserBaseMinimumSerializer(read_only=True)

    class Meta:
        model = AssetServiceEdit
        exclude = ("asset_service",)


class AssetServiceSerializer(ModelSerializer):
    id = UUIDField(source="external_id", read_only=True)
    edits = AssetServiceEditSerializer(many=True, read_only=True)

    class Meta:
        model = AssetService
        exclude = ("deleted", "asset")

    def update(self, instance, validated_data):
        user = self.context["request"].user
        serviced_on = validated_data.get("serviced_on", instance.serviced_on)
        note = validated_data.get("note", instance.note)
        if serviced_on == instance.serviced_on and note == instance.note:
            return instance

        with transaction.atomic():
            edit = AssetServiceEdit(
                asset_service=instance,
                edited_on=now(),
                edited_by=user,
                serviced_on=serviced_on,
                note=note,
            )
            edit.save()

            updated_instance = super().update(instance, validated_data)

        return updated_instance


class AssetSerializer(ModelSerializer):
    id = UUIDField(source="external_id", read_only=True)
    status = ChoiceField(choices=StatusChoices, read_only=True)
    asset_type = ChoiceField(choices=AssetTypeChoices)
    location_object = AssetLocationSerializer(source="current_location", read_only=True)
    location = UUIDField(write_only=True, required=True)
    last_service = AssetServiceSerializer(read_only=True)
    last_serviced_on = serializers.DateField(write_only=True, required=False)
    note = serializers.CharField(write_only=True, required=False, allow_blank=True)

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
        if warranty_amc_end_of_validity := attrs.get("warranty_amc_end_of_validity"):
            # pop out warranty date if it is not changed
            if (
                self.instance
                and self.instance.warranty_amc_end_of_validity
                == warranty_amc_end_of_validity
            ):
                del attrs["warranty_amc_end_of_validity"]

            elif warranty_amc_end_of_validity < datetime.now().date():
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

    def create(self, validated_data):
        last_serviced_on = validated_data.pop("last_serviced_on", None)
        note = validated_data.pop("note", None)
        with transaction.atomic():
            asset_instance = super().create(validated_data)
            if last_serviced_on or note:
                asset_service = AssetService(
                    asset=asset_instance, serviced_on=last_serviced_on, note=note
                )
                asset_service.save()
                asset_instance.last_service = asset_service
                asset_instance.save(update_fields=["last_service"])
        return asset_instance

    def update(self, instance, validated_data):
        user = self.context["request"].user
        with transaction.atomic():
            if validated_data.get("last_serviced_on") and (
                not instance.last_service
                or instance.last_service.serviced_on
                != validated_data.get(
                    "last_serviced_on", instance.last_service.serviced_on
                )
                or instance.last_service.note
                != validated_data.get("note", instance.last_service.note)
            ):
                asset_service = AssetService(
                    asset=instance,
                    serviced_on=validated_data.get("last_serviced_on"),
                    note=validated_data.get("note"),
                )
                asset_service_initial_edit = AssetServiceEdit(
                    asset_service=asset_service,
                    edited_on=now(),
                    edited_by=user,
                    serviced_on=asset_service.serviced_on,
                    note=asset_service.note,
                )
                asset_service.save()
                asset_service_initial_edit.save()
                instance.last_service = asset_service

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


class AssetTransactionSerializer(ModelSerializer):
    id = UUIDField(source="external_id", read_only=True)
    asset = AssetBareMinimumSerializer(read_only=True)
    from_location = AssetLocationSerializer(read_only=True)
    to_location = AssetLocationSerializer(read_only=True)
    performed_by = UserBaseMinimumSerializer(read_only=True)

    class Meta:
        model = AssetTransaction
        exclude = ("deleted", "external_id")


class AssetAvailabilitySerializer(ModelSerializer):
    id = UUIDField(source="external_id", read_only=True)
    asset = AssetBareMinimumSerializer(read_only=True)

    class Meta:
        model = AssetAvailabilityRecord
        exclude = ("deleted", "external_id")


class UserDefaultAssetLocationSerializer(ModelSerializer):
    location_object = AssetLocationSerializer(source="location", read_only=True)

    class Meta:
        model = UserDefaultAssetLocation
        exclude = ("deleted", "external_id", "location", "user", "id")


class AssetActionSerializer(Serializer):
    def actionChoices():
        actions = [
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

    class Meta:
        fields = ("type", "data")


class DummyAssetOperateSerializer(Serializer):
    action = AssetActionSerializer(required=True)

    class Meta:
        fields = ("action",)


class DummyAssetOperateResponseSerializer(Serializer):
    message = CharField(required=True)
    result = JSONField(required=False)

    class Meta:
        fields = ("message", "result")
