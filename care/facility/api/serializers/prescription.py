from rest_framework import serializers
from care.facility.models import Prescription, MedicineAdministration
from care.users.api.serializers.user import (
    UserAssignedSerializer,
    UserBaseMinimumSerializer,
)

class PrescriptionSerializer(serializers.ModelSerializer):

    prescribed_by = UserBaseMinimumSerializer(read_only=True)
    consultation = serializers.CharField(source="consultation.external_id", read_only=True)

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
        )
        read_only_fields = (
            "external_id",
            "consultation"
            "prescribed_by",
            "created_date",
            "modified_date",
            "discontinued_date",
        )
class MedicineAdministrationSerializer(serializers.ModelSerializer):

    administered_by = UserBaseMinimumSerializer(read_only=True)
    prescription = PrescriptionSerializer(read_only=True)

    class Meta:
        model = MedicineAdministration
        fields = (
            "external_id",
            "prescription",
            "notes",
            "administered_by",
            "created_date",
            "modified_date",
        )
        read_only_fields = (
            "external_id",
            "administered_by",
            "created_date",
            "modified_date",
        )