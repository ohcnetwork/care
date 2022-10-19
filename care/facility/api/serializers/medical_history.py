from django.db import transaction
from rest_framework import serializers

from care.facility.models import MedicalHistory, PatientRegistration
from care.facility.models.patient import Diseases
from care.facility.models.patient_consultation import PatientConsultation
from care.utils.serializer.external_id_field import ExternalIdSerializerField


class DiseaseSerializer(serializers.ModelSerializer):
    date = serializers.DateField()

    class Meta:
        model = Diseases
        fields = (
            "disease",
            "details",
            "date",
            "precision",
        )


class MedicalHistorySerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="external_id", read_only=True)

    patient = ExternalIdSerializerField(
        queryset=PatientRegistration.objects.all(), required=False
    )

    consultation = ExternalIdSerializerField(
        queryset=PatientConsultation.objects.all(), required=False
    )

    patient_diseases = serializers.ListSerializer(
        child=DiseaseSerializer(),
        required=False,
    )

    class Meta:
        model = MedicalHistory
        exclude = ("deleted", "external_id")

    def create(self, validated_data):
        with transaction.atomic():
            consultation = validated_data["consultation"]
            patient_diseases = validated_data.pop("patient_diseases", [])
            medical_history = super().create(validated_data)
            diseases = []
            for disease in patient_diseases:
                diseases.append(
                    Diseases(
                        medical_history=medical_history,
                        **disease,
                    )
                )
            if diseases:
                Diseases.objects.bulk_create(diseases, ignore_conflicts=True)
            consultation.last_medical_history = medical_history
            consultation.save(update_fields=["last_medical_history"])
            return medical_history

    def update(self, instance, validated_data):
        with transaction.atomic():
            patient_diseases = validated_data.pop("patient_diseases", [])
            medical_history = super().update(instance, validated_data)
            Diseases.objects.filter(medical_history=medical_history).update(
                deleted=True
            )
            diseases = []
            for disease in patient_diseases:
                diseases.append(
                    Diseases(
                        medical_history=medical_history,
                        **disease,
                    )
                )
            if diseases:
                Diseases.objects.bulk_create(diseases, ignore_conflicts=True)
            return medical_history
