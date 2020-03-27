from rest_framework import fields, serializers

from care.facility.models import (
    MEDICAL_HISTORY_CHOICES,
    PatientRegistration,
    PatientTeleConsultation,
)


class PatientSerializer(serializers.ModelSerializer):
    medical_history = fields.MultipleChoiceField(choices=MEDICAL_HISTORY_CHOICES)

    class Meta:
        model = PatientRegistration
        exclude = ("created_by", "deleted")


class PatientTeleConsultationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientTeleConsultation
        fields = "__all__"


class PatientDetailSerializer(PatientSerializer):
    tele_consultation_history = serializers.ListSerializer(child=PatientTeleConsultationSerializer(), read_only=True)
