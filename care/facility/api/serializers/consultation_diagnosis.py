from typing import Any

from rest_framework import serializers

from care.facility.models import (
    INACTIVE_CONDITION_VERIFICATION_STATUSES,
    ConsultationDiagnosis,
)
from care.facility.models.icd11_diagnosis import ICD11Diagnosis
from care.facility.static_data.icd11 import get_icd11_diagnosis_object_by_id
from care.users.api.serializers.user import UserBaseMinimumSerializer


class ConsultationCreateDiagnosisSerializer(serializers.ModelSerializer):
    def validate_verification_status(self, value):
        if value in INACTIVE_CONDITION_VERIFICATION_STATUSES:
            msg = "Verification status not allowed"
            raise serializers.ValidationError(msg)
        return value

    class Meta:
        model = ConsultationDiagnosis
        fields = ("diagnosis", "verification_status", "is_principal")


class ConsultationDiagnosisSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)
    diagnosis = serializers.PrimaryKeyRelatedField(
        queryset=ICD11Diagnosis.objects.all(), required=True, allow_null=False
    )
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
        if self.instance and value != self.instance.diagnosis:
            msg = "Diagnosis cannot be changed"
            raise serializers.ValidationError(msg)

        if (
            not self.instance
            and ConsultationDiagnosis.objects.filter(
                consultation__external_id=self.get_consultation_external_id(),
                diagnosis=value,
            ).exists()
        ):
            msg = "Diagnosis already exists for consultation"
            raise serializers.ValidationError(msg)

        return value

    def validate_verification_status(self, value):
        if not self.instance and value in INACTIVE_CONDITION_VERIFICATION_STATUSES:
            msg = "Verification status not allowed"
            raise serializers.ValidationError(msg)
        return value

    def validate_is_principal(self, value):
        if not value:
            return value

        qs = ConsultationDiagnosis.objects.filter(
            consultation__external_id=self.get_consultation_external_id(),
            is_principal=True,
        )

        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if qs.exists():
            msg = "Consultation already has a principal diagnosis. Unset the existing principal diagnosis first."
            raise serializers.ValidationError(msg)

        return value

    def update(self, instance, validated_data):
        if (
            "verification_status" in validated_data
            and validated_data["verification_status"]
            in INACTIVE_CONDITION_VERIFICATION_STATUSES
        ):
            instance.is_principal = False
        return super().update(instance, validated_data)

    def validate(self, attrs: Any) -> Any:
        validated = super().validate(attrs)

        if (
            "verification_status" in validated
            and validated["verification_status"]
            in INACTIVE_CONDITION_VERIFICATION_STATUSES
        ):
            validated["is_principal"] = False

        if validated.get("is_principal"):
            verification_status = validated.get(
                "verification_status",
                self.instance.verification_status if self.instance else None,
            )
            if verification_status in INACTIVE_CONDITION_VERIFICATION_STATUSES:
                raise serializers.ValidationError(
                    {
                        "is_principal": "Refuted/Entered in error diagnoses cannot be marked as Principal Diagnosis"
                    }
                )

        return validated
