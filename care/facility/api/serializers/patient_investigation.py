from rest_framework import serializers

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.api.serializers.patient_consultation import (
    PatientConsultationSerializer,
)
from care.facility.models.patient_investigation import (
    InvestigationSession,
    InvestigationValue,
    PatientInvestigation,
    PatientInvestigationGroup,
)


class PatientInvestigationGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientInvestigationGroup
        exclude = TIMESTAMP_FIELDS + ("id",)


class PatientInvestigationSerializer(serializers.ModelSerializer):
    groups = PatientInvestigationGroupSerializer(many=True)

    class Meta:
        model = PatientInvestigation
        exclude = TIMESTAMP_FIELDS + ("id",)


class MinimalPatientInvestigationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientInvestigation
        exclude = TIMESTAMP_FIELDS + ("id", "groups")


class PatientInvestigationSessionSerializer(serializers.ModelSerializer):
    session_external_id = serializers.UUIDField(source="external_id")
    session_created_date = serializers.DateTimeField(source="created_date")

    class Meta:
        model = InvestigationSession
        exclude = TIMESTAMP_FIELDS + ("external_id", "id")


class InvestigationValueSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="external_id", read_only=True)

    consultation_object = PatientConsultationSerializer(
        source="consultation", read_only=True
    )

    group_object = PatientInvestigationGroupSerializer(source="group", read_only=True)
    investigation_object = MinimalPatientInvestigationSerializer(
        source="investigation", read_only=True
    )
    session_object = PatientInvestigationSessionSerializer(
        source="session", read_only=True
    )

    class Meta:
        model = InvestigationValue
        read_only_fields = TIMESTAMP_FIELDS + (
            "session_id",
            "investigation",
            "consultation",
            "session",
        )
        exclude = TIMESTAMP_FIELDS + ("external_id",)

    def update(self, instance, validated_data):
        if instance.consultation.discharge_date:
            raise serializers.ValidationError(
                {"consultation": ["Discharged Consultation data cannot be updated"]}
            )

        # Removed since it might flood messages
        # NotificationGenerator(
        #     event=Notification.Event.INVESTIGATION_UPDATED,
        #     caused_by=self.context["request"].user,
        #     caused_object=instance,
        #     facility=instance.consultation.patient.facility,
        # ).generate()

        return super().update(instance, validated_data)


class InvestigationValueCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvestigationValue
        read_only_fields = TIMESTAMP_FIELDS
        exclude = TIMESTAMP_FIELDS + ("external_id",)


class ValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvestigationValue
        fields = ("external_id", "value", "notes")


# Dummy for Spec
class InvestigationUpdateSerializer(serializers.Serializer):
    investigations = ValueSerializer(many=True)

    class Meta:
        fields = ("investigations",)
