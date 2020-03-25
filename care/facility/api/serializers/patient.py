from rest_framework import serializers, fields

from care.facility.models import PatientRegistration, MEDICAL_HISTORY_CHOICES, PatientTeleConsultation


class PatientSerializer(serializers.ModelSerializer):
    medical_history = fields.MultipleChoiceField(choices=MEDICAL_HISTORY_CHOICES)

    class Meta:
        model = PatientRegistration
        fields = '__all__'


class PatientTeleConsultationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientTeleConsultation
        fields = '__all__'


class PatientDetailSerializer(PatientSerializer):
    tele_consultation_history = serializers.ListSerializer(
        child=PatientTeleConsultationSerializer(), read_only=True)

