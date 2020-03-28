from rest_framework import fields, serializers

from care.facility.api.serializers.patient_consultation import PatientConsultationSerializer
from care.facility.models import (
    MEDICAL_HISTORY_CHOICES,
    PatientConsultation,
    PatientRegistration,
    PatientTeleConsultation,
)


class PatientSerializer(serializers.ModelSerializer):
    medical_history = fields.MultipleChoiceField(choices=MEDICAL_HISTORY_CHOICES)
    last_consultation = serializers.SerializerMethodField()

    def get_last_consultation(self, obj):
        last_consultation = PatientConsultation.objects.filter(patient=obj).last()
        if last_consultation:
            return PatientConsultationSerializer(last_consultation).data
        return None

    class Meta:
        model = PatientRegistration
        exclude = ("created_by", "deleted")


class PatientTeleConsultationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientTeleConsultation
        fields = "__all__"


class PatientDetailSerializer(PatientSerializer):
    tele_consultation_history = serializers.ListSerializer(child=PatientTeleConsultationSerializer(), read_only=True)
