from rest_framework import fields, serializers

from care.facility.models import (
    MEDICAL_HISTORY_CHOICES,
    PatientAdmission,
    PatientRegistration,
    PatientTeleConsultation,
)


class PatientSerializer(serializers.ModelSerializer):
    medical_history = fields.MultipleChoiceField(choices=MEDICAL_HISTORY_CHOICES)
    admitted_at = serializers.SerializerMethodField(source="", read_only=True)

    def get_admitted_at(self, obj):
        try:
            return PatientAdmission.objects.only("facility_id").get(patient_id=obj.id, is_active=True).facility_id
        except PatientAdmission.DoesNotExist:
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


class PatientAdmissionSerializer(serializers.Serializer):
    facility_id = serializers.IntegerField()
    patient_id = serializers.IntegerField()
    admission_date = serializers.DateTimeField(required=False)
    discharge_date = serializers.DateTimeField(required=False)
    is_active = serializers.BooleanField(read_only=True)
