from rest_framework import serializers
from care.facility.models import Prescription, PRNPrescription, MedicineAdministration
from care.users.api.serializers.user import (
    UserAssignedSerializer,
    UserBaseMinimumSerializer,
)

class PrescriptionSerializer(serializers.ModelSerializer):

    prescribed_by = UserBaseMinimumSerializer(read_only=True)

    class Meta:
        model = Prescription
        fields = (
            "external_id",
            "medicine",
            "route",
            "dosage",
            "frequency",
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
            "prescribed_by",
            "created_date",
            "modified_date",
            "discontinued_date",
        )

class PRNPrescriptionSerializer(serializers.ModelSerializer):

    prescribed_by = UserBaseMinimumSerializer(read_only=True)

    class Meta:
        model = PRNPrescription
        fields = (
            "external_id",
            "medicine",
            "route",
            "dosage",
            "indicator",
            "max_dosage",
            "min_hours_between_doses",
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
            "prescribed_by",
            "created_date",
            "modified_date",
            "discontinued_date",
        )

class MedicineAdministrationSerializer(serializers.ModelSerializer):

    administered_by = UserBaseMinimumSerializer(read_only=True)
    prescription = PrescriptionSerializer(read_only=True)
    prn_prescription = PRNPrescriptionSerializer(read_only=True)

    class Meta:
        model = MedicineAdministration
        fields = (
            "external_id",
            "prescription",
            "prn_prescription",
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