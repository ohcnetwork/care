from rest_framework import serializers

from care.facility.models import PatientConsultation, PatientRegistration
from care.facility.api.serializers.facility import FacilityBasicInfoSerializer

from config.serializers import ChoiceField


class MinimalPatientSerializer(serializers.ModelSerializer):

    id = serializers.CharField(source="external_id")

    class Meta:
        model = PatientRegistration
        fields = ("id", "name", "phone_number", "address")


class PrescriptionSupplierConsultationSerializer(serializers.ModelSerializer):

    id = serializers.CharField(source="external_id", read_only=True)
    patient = MinimalPatientSerializer(read_only=True)

    class Meta:
        model = PatientConsultation
        fields = ("id", "prescriptions", "discharge_advice", "patient")
