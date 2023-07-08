from django.db import transaction
from django.forms import ChoiceField
from rest_framework import serializers

from care.facility.models import PatientConsultation, PatientHealthDetails
from care.facility.models.patient import VaccinationHistory
from care.facility.models.patient_base import BLOOD_GROUP_CHOICES
from care.utils.queryset.facility import get_home_facility_queryset
from care.utils.serializer.external_id_field import ExternalIdSerializerField


class VaccinationHistorySerializer(serializers.ModelSerializer):
    doses = serializers.IntegerField(required=False, default=0)
    date = serializers.DateField()

    class Meta:
        model = VaccinationHistory
        fields = ("vaccine", "doses", "date", "precision")


class PatientHealthDetailsSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)

    consultation = ExternalIdSerializerField(
        queryset=PatientConsultation.objects.all(), required=False
    )
    blood_group = ChoiceField(choices=BLOOD_GROUP_CHOICES, required=True)

    vaccination_history = serializers.ListSerializer(
        child=VaccinationHistorySerializer(), required=False
    )

    class Meta:
        model = PatientHealthDetails
        exclude = ("deleted", "external_id")

    def create(self, validated_data):
        with transaction.atomic():
            consultation = validated_data["consultation"]
            vaccination_history = validated_data.pop("vaccination_history", [])
            allowed_facilities = get_home_facility_queryset(
                self.context["request"].user
            )
            if not allowed_facilities.filter(id=consultation.facility.id).exists():
                raise serializers.ValidationError(
                    {
                        "patient": "Patient Health Details creates are only allowed in home facility"
                    }
                )

            health_details = super().create(validated_data)
            vaccines = []
            for vaccine in vaccination_history:
                vaccines.append(
                    VaccinationHistory(
                        health_details=health_details,
                        **vaccine,
                    )
                )
            if vaccines:
                VaccinationHistory.objects.bulk_create(vaccines, ignore_conflicts=True)
            consultation.health_details = health_details
            consultation.save(update_fields=["health_details"])
            return health_details

    def update(self, instance, validated_data):
        with transaction.atomic():
            vaccination_history = validated_data.pop("vaccination_history", [])
            health_details = super().update(instance, validated_data)
            VaccinationHistory.objects.filter(health_details=health_details).update(
                deleted=True
            )
            vaccines = []
            for vaccine in vaccination_history:
                vaccines.append(
                    VaccinationHistory(
                        health_details=health_details,
                        **vaccine,
                    )
                )
            if vaccines:
                VaccinationHistory.objects.bulk_create(vaccines, ignore_conflicts=True)
            return health_details
