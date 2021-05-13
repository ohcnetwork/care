from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework import serializers

from care.facility.models import (
    FacilityInventoryBurnRate,
    FacilityInventoryItem,
    FacilityInventoryItemTag,
    FacilityInventoryLog,
    FacilityInventoryMinQuantity,
    FacilityInventorySummary,
    FacilityInventoryUnit,
    FacilityInventoryUnitConverter,
)


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
        read_only_fields = ("id", "external_id", "created_by", "current_stock", "quantity_in_default_unit")
        exclude = ("deleted", "modified_date", "facility")

    @transaction.atomic
    def create(self, validated_data):

        item = validated_data["item"]
        unit = validated_data["unit"]
        facility = validated_data["facility"]

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
        validated_data["quantity_in_default_unit"] = abs(current_quantity)
        try:
            summary_obj = FacilityInventorySummary.objects.get(facility=facility, item=item)
            current_quantity = summary_obj.quantity + (multiplier * validated_data["quantity"])
            summary_obj.quantity = F("quantity") + (multiplier * validated_data["quantity"])
        except:
            summary_obj = FacilityInventorySummary(
                facility=facility, item=item, quantity=multiplier * validated_data["quantity"]
            )

        if current_quantity < 0:
            raise serializers.ValidationError({"stock": [f"Stock not Available"]})

        try:
            current_min_quantity = FacilityInventoryMinQuantity.objects.get(facility=facility, item=item).min_quantity
        except:
            pass

        summary_obj.is_low = current_quantity < current_min_quantity

        validated_data["current_stock"] = current_quantity

        if not validated_data["is_incoming"]:
            self._set_burn_rate(facility, item, validated_data["quantity"])

        instance = super().create(validated_data)
        summary_obj.save()

        return instance

    def _set_burn_rate(self, facility, item, qty):
        previous_usage_log = (
            FacilityInventoryLog.objects.filter(facility=facility, item=item, is_incoming=False)
            .order_by("-id")
            .first()
        )

        if previous_usage_log:
            time_diff = (timezone.now() - previous_usage_log.created_date).seconds
            if time_diff:
                burn_rate = qty / (time_diff / 3600.0)
            else:
                burn_rate = 0
            FacilityInventoryBurnRate.objects.update_or_create(
                facility=facility, item=item, defaults={"burn_rate": burn_rate}
            )


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


class FacilityInventoryBurnRateSerializer(serializers.ModelSerializer):
    facility_id = serializers.CharField(source="facility.external_id")
    facility_name = serializers.CharField(source="facility.name")
    item_name = serializers.CharField(source="item.name")
    unit_id = serializers.CharField(source="item.default_unit.id")
    unit_name = serializers.CharField(source="item.default_unit.name")

    class Meta:
        model = FacilityInventoryBurnRate
        FIELDS = (
            "facility_id",
            "facility_name",
            "item_id",
            "item_name",
            "burn_rate",
            "unit_id",
            "unit_name",
            # 'current_stock'
        )
        fields = FIELDS
        read_only_fields = FIELDS
