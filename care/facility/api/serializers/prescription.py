from rest_framework import serializers
from care.facility.models import Prescription, MedicineAdministration
from care.users.api.serializers.user import (
    UserAssignedSerializer,
    UserBaseMinimumSerializer,
)

class MedicineAdministrationSerializer(serializers.ModelSerializer):

    administered_by = UserBaseMinimumSerializer(read_only=True)

    class Meta:
        model = MedicineAdministration
        fields = (
            "external_id",
            "notes",
            "administered_by",
            "created_date",
            "administered_date"
            "modified_date",
        )
        read_only_fields = (
            "external_id",
            "administered_by",
            "created_date",
            "modified_date",
        )
class PrescriptionSerializer(serializers.ModelSerializer):

    prescribed_by = UserBaseMinimumSerializer(read_only=True)
    consultation = serializers.CharField(source="consultation.external_id", read_only=True)
    administrations = MedicineAdministrationSerializer(many=True, read_only=True)

    class Meta:
        model = Prescription
        fields = (
            "external_id",
            "consultation",
            "medicine",
            "route",
            "dosage",
            "frequency",
            "indicator",
            "max_dosage",
            "is_prn",
            "min_hours_between_doses",
            "days",
            "notes",
            "meta",
            "prescribed_by",
            "discontinued",
            "discontinued_reason",
            "discontinued_date",
            "created_date",
            "modified_date",
            "administrations",
        )
        read_only_fields = (
            "external_id",
            "consultation"
            "prescribed_by",
            "created_date",
            "modified_date",
            "discontinued_date",
            "administrations",
        )

    def validate(self, attrs):
        if attrs.get("is_prn") and attrs.get("is_prn") is True:
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