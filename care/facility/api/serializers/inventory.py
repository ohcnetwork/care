from django.db.models import F
from rest_framework import serializers

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.models import (
    ROOM_TYPES,
    FacilityInventoryItem,
    FacilityInventoryItemTag,
    FacilityInventoryLog,
    FacilityInventorySummary,
    FacilityInventoryUnit,
    FacilityInventoryUnitConverter,
    FacilityInventoryMinQuantity,
)

from config.serializers import ChoiceField


class FacilityInventoryItemTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = FacilityInventoryItemTag
        read_only_fields = ("id",)
        fields = "__all__"


class FacilityInventoryUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = FacilityInventoryUnit
        read_only_fields = ("id",)
        fields = "__all__"


class FacilityInventoryItemSerializer(serializers.ModelSerializer):
    default_unit = FacilityInventoryUnitSerializer()
    allowed_units = FacilityInventoryUnitSerializer(many=True)
    tags = FacilityInventoryItemTagSerializer(many=True)

    class Meta:
        model = FacilityInventoryItem
        read_only_fields = ("id",)
        fields = "__all__"


class FacilityInventoryLogSerializer(serializers.ModelSerializer):

    id = serializers.UUIDField(source="external_id", read_only=True)

    item_object = FacilityInventoryItemSerializer(source="item", required=False)
    unit_object = FacilityInventoryUnitSerializer(source="unit", required=False)

    class Meta:
        model = FacilityInventoryLog
        read_only_fields = ("id", "external_id", "created_by")
        exclude = (
            "deleted",
            "modified_date",
            "facility",
        )

    def create(self, validated_data):

        item = validated_data["item"]
        unit = validated_data["unit"]

        try:
            item.allowed_units.get(id=unit.id)
        except:
            raise serializers.ValidationError({"unit": [f"Item cannot be measured with unit"]})

        multiplier = 1

        try:
            if item.default_unit != unit:
                multiplier = FacilityInventoryUnitConverter.objects.get(
                    from_unit=unit, to_unit=item.default_unit
                ).multiplier
        except:
            raise serializers.ValidationError({"item": [f"Please Ask Admin to Add Conversion Metrics"]})

        validated_data["created_by"] = self.context["request"].user

        if not validated_data["is_incoming"]:
            multiplier *= -1

        summary_obj = None
        current_min_quantity = item.min_quantity
        current_quantity = multiplier * validated_data["quantity"]
        try:
            summary_obj = FacilityInventorySummary.objects.get(facility=validated_data["facility"], item=item)
            current_quantity = summary_obj.quantity + (multiplier * validated_data["quantity"])
            summary_obj.quantity = F("quantity") + (multiplier * validated_data["quantity"])
        except:
            summary_obj = FacilityInventorySummary(
                facility=validated_data["facility"], item=item, quantity=multiplier * validated_data["quantity"]
            )

        try:
            current_min_quantity = FacilityInventoryMinQuantity.objects.get(
                facility=validated_data["facility"], item=item
            ).min_quantity
        except:
            pass

        summary_obj.is_low = current_quantity < current_min_quantity

        instance = super().create(validated_data)
        summary_obj.save()

        return instance


class FacilityInventorySummarySerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)

    item_object = FacilityInventoryItemSerializer(source="item", required=False)
    unit_object = FacilityInventoryUnitSerializer(source="unit", required=False)

    class Meta:
        model = FacilityInventorySummary
        read_only_fields = ("id", "item", "unit")
        exclude = (
            "external_id",
            "deleted",
            "modified_date",
            "facility",
        )


class FacilityInventoryMinQuantitySerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)

    item_object = FacilityInventoryItemSerializer(source="item", required=False)

    class Meta:
        model = FacilityInventoryMinQuantity
        read_only_fields = ("id", "unit")
        exclude = (
            "external_id",
            "deleted",
            "modified_date",
            "facility",
        )

    def create(self, validated_data):
        item = validated_data["item"]

        if not item:
            raise serializers.ValidationError({"item": [f"Item cannot be Null"]})

        try:
            instance = super().create(validated_data)
        except:
            raise serializers.ValidationError({"item": [f"Item min quantity already set"]})

        try:
            summary_obj = FacilityInventorySummary.objects.get(facility=validated_data["facility"], item=item)
            summary_obj.is_low = summary_obj.quantity < validated_data["min_quantity"]
            summary_obj.save()
        except:
            pass

        return instance

    def update(self, instance, validated_data):

        if "item" in validated_data:
            if instance.item != validated_data["item"]:
                raise serializers.ValidationError({"item": [f"Item cannot be Changed"]})

        item = validated_data["item"]

        try:
            summary_obj = FacilityInventorySummary.objects.get(facility=instance.facility, item=item)
            summary_obj.is_low = summary_obj.quantity < validated_data["min_quantity"]
            summary_obj.save()
        except:
            pass

        return super().update(instance, validated_data)
