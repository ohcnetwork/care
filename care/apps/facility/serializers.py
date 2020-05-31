from django.utils.translation import ugettext as _

from rest_framework import serializers as rest_serializers

from apps.facility import models as facility_models


class FacilityShortSerializer(rest_serializers.ModelSerializer):
    class Meta:
        model = facility_models.Facility
        fields = (
            "id",
            "name",
        )


class FacilitySerializer(rest_serializers.ModelSerializer):
    class Meta:
        model = facility_models.Facility
        fields = (
            "id",
            "name",
            "facility_code",
            "facility_type",
            "location",
            "address",
            "local_body",
            "district",
            "state",
            "phone_number",
            "corona_testing",
            "created_by",
            "owned_by",
            "total_patient",
            "positive_patient",
            "negative_patient",
        )


class FacilityUserSerializer(rest_serializers.ModelSerializer):
    class Meta:
        model = facility_models.FacilityUser
        fields = (
            "facility",
            "user",
            "created_by",
        )


class FacilityTypeSerializer(rest_serializers.ModelSerializer):
    class Meta:
        model = facility_models.FacilityType
        fields = (
            "id",
            "name",
        )


class FacilityStaffSerializer(rest_serializers.ModelSerializer):
    class Meta:
        model = facility_models.FacilityStaff
        fields = (
            "id",
            "facility",
            "name",
            "phone_number",
            "email",
            "designation",
        )


class FacilityInfrastructureSerializer(rest_serializers.ModelSerializer):
    class Meta:
        model = facility_models.FacilityInfrastructure
        fields = ("facility", "room_type", "bed_type", "total_bed", "occupied_bed", "available_bed", "updated_at")


class InventorySerializer(rest_serializers.ModelSerializer):
    class Meta:
        model = facility_models.Inventory
        fields = (
            "id",
            "facility",
            "item",
            "required_quantity",
            "current_quantity",
            "updated_at",
        )
        extra_kwargs = {
            "required_quantity": {"required": True},
            "current_quantity": {"required": True},
            "updated_at": {"read_only": True},
        }
        validators = [
            rest_serializers.UniqueTogetherValidator(
                queryset=model.objects.all(),
                fields=("facility", "item"),
                message=_("This Inventory have already added, Update existing one."),
            )
        ]

    def validate(self, attrs):
        attrs["updated_by"] = self.context["request"].user
        return super(InventorySerializer, self).validate(attrs)


class InventoryUpdateSerializer(InventorySerializer):
    class Meta(InventorySerializer.Meta):
        fields = (
            "id",
            "required_quantity",
            "current_quantity",
        )


class InventoryItemSerializer(rest_serializers.ModelSerializer):
    class Meta:
        model = facility_models.InventoryItem
        fields = (
            "id",
            "name",
        )


class RoomTypeSerializer(rest_serializers.ModelSerializer):
    class Meta:
        model = facility_models.RoomType
        fields = ("id", "name", "description")


class BedTypeSerializer(rest_serializers.ModelSerializer):
    class Meta:
        model = facility_models.RoomType
        fields = ("id", "name", "description")
