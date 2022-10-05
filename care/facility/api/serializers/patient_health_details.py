from django.forms import ChoiceField
from rest_framework import serializers

from care.facility.models import (
    PatientConsultation,
    PatientHealthDetails,
    PatientRegistration,
)
from care.facility.models.facility import Facility
from care.facility.models.patient_base import BLOOD_GROUP_CHOICES
from care.utils.queryset.facility import get_home_facility_queryset
from care.utils.serializer.external_id_field import ExternalIdSerializerField


class PatientHealthDetailsSerializer(serializers.ModelSerializer):

    id = serializers.CharField(source="external_id", read_only=True)

    patient = ExternalIdSerializerField(
        queryset=PatientRegistration.objects.all(), required=False
    )
    facility = ExternalIdSerializerField(
        queryset=Facility.objects.all(), required=False
    )
    consultation = ExternalIdSerializerField(
        queryset=PatientConsultation.objects.all(), required=False
    )
    blood_group = ChoiceField(choices=BLOOD_GROUP_CHOICES, required=True)

    class Meta:
        model = PatientHealthDetails
        exclude = ("deleted", "external_id")

    def create(self, validated_data):
        consultation = validated_data["consultation"]
        allowed_facilities = get_home_facility_queryset(self.context["request"].user)
        if not allowed_facilities.filter(
            id=self.validated_data["patient"].facility.id
        ).exists():
            raise serializers.ValidationError(
                {
                    "patient": "Patient Health Details creates are only allowed in home facility"
                }
            )

        health_details = super().create(validated_data)
        consultation.last_health_details = health_details
        consultation.save(update_fields=["last_health_details"])
        return health_details

    def update(self, instance, validated_data):
        consultation = validated_data["consultation"]
        health_details = super().update(instance, validated_data)
        consultation.last_health_details = health_details
        consultation.save(update_fields=["last_health_details"])
        return health_details
