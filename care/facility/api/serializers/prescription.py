from rest_framework import serializers

from care.facility.models import Prescription, MedicineAdministration
from care.users.api.serializers.user import (
    UserBaseMinimumSerializer,
)


class MedicineAdministrationSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)

    administered_by = UserBaseMinimumSerializer(read_only=True)

    class Meta:
        model = MedicineAdministration
        fields = (
            "external_id",
            "notes",
            "administered_by",
            "created_date",
            "administered_date",
            "modified_date",
        )
        read_only_fields = (
            "external_id",
            "administered_by",
            "created_date",
            "modified_date",
        )


class PrescriptionSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)

    prescribed_by = UserBaseMinimumSerializer(read_only=True)

    class Meta:
        model = Prescription
        exclude = (
            "consultation",
            "daily_round",
            "deleted",
        )
        read_only_fields = (
            "external_id",
            "prescribed_by",
            "created_date",
            "modified_date",
            "discontinued_date",
            "is_migrated"
        )

    def validate(self, attrs):
        if attrs.get("is_prn"):
            if not attrs.get("indicator"):
                raise serializers.ValidationError(
                    {"indicator": "Indicator should be set for PRN prescriptions."}
                )

        else:
            if not attrs.get("frequency"):
                raise serializers.ValidationError(
                    {"frequency": "Frequency should be set for prescriptions."}
                )
        return super().validate(attrs)
