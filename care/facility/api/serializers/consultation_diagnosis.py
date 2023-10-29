from rest_framework import serializers

from care.facility.models import (
    INACTIVE_CONDITION_VERIFICATION_STATUSES,
    ConsultationDiagnosis,
)
from care.facility.static_data.icd11 import get_icd11_diagnosis_object_by_id
from care.users.api.serializers.user import UserBaseMinimumSerializer


class ConsultationCreateDiagnosisSerializer(serializers.ModelSerializer):
    diagnosis = serializers.UUIDField(write_only=True)

    def validate_verification_status(self, value):
        if value in INACTIVE_CONDITION_VERIFICATION_STATUSES:
            raise serializers.ValidationError("Verification status not allowed")
        return value

    class Meta:
        model = ConsultationDiagnosis
        fields = ("diagnosis", "verification_status", "is_principal")


class ConsultationDiagnosisSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)
    diagnosis = serializers.UUIDField(write_only=True)
    diagnosis_object = serializers.SerializerMethodField()
    created_by = UserBaseMinimumSerializer(read_only=True)

    def get_diagnosis_object(self, obj):
        return get_icd11_diagnosis_object_by_id(obj.diagnosis_id, as_dict=True)

    class Meta:
        model = ConsultationDiagnosis
        exclude = (
            "consultation",
            "external_id",
            "deleted",
        )
        read_only_fields = (
            "is_principal",
            "created_by",
            "created_date",
            "modified_date",
            "is_migrated",
        )

    def get_consultation_external_id(self):
        return self.context["request"].parser_context["kwargs"][
            "consultation_external_id"
        ]

    def validate_diagnosis(self, value):
        if not get_icd11_diagnosis_object_by_id(value):
            raise serializers.ValidationError("Invalid Diagnosis")

        if ConsultationDiagnosis.objects.filter(
            consultation__external_id=self.get_consultation_external_id(),
            diagnosis_id=value,
        ).exists():
            raise serializers.ValidationError(
                "Diagnosis already exists for consultation"
            )

        return value

    def validate_verification_status(self, value):
        if not self.instance and value in INACTIVE_CONDITION_VERIFICATION_STATUSES:
            raise serializers.ValidationError("Verification status not allowed")
        return value

    def update(self, instance, validated_data):
        if (
            "verification_status" in validated_data
            and validated_data["verification_status"]
            in INACTIVE_CONDITION_VERIFICATION_STATUSES
        ):
            instance.is_principal = False
        return super().update(instance, validated_data)

    def validate(self, attrs):
        if self.instance:
            attrs.pop("diagnosis", None)
        return attrs
