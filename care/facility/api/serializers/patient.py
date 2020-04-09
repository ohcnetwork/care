import datetime

from django.db import transaction
from django.utils.timezone import make_aware
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.api.serializers.facility import FacilityBasicInfoSerializer, FacilitySerializer
from care.facility.api.serializers.patient_consultation import PatientConsultationSerializer
from care.facility.models import (
    DISEASE_CHOICES,
    GENDER_CHOICES,
    Disease,
    Facility,
    FacilityPatientStatsHistory,
    PatientRegistration,
    PatientSearch,
)
from care.facility.models.patient_base import DISEASE_STATUS_CHOICES, DiseaseStatusEnum
from care.facility.models.patient_consultation import PatientConsultation
from care.facility.models.patient_tele_consultation import PatientTeleConsultation
from care.users.api.serializers.lsg import DistrictSerializer, LocalBodySerializer, StateSerializer
from config.serializers import ChoiceField


class PatientListSerializer(serializers.ModelSerializer):
    facility = serializers.IntegerField(source="facility_id", allow_null=True, read_only=True)
    facility_object = FacilityBasicInfoSerializer(source="facility", read_only=True)
    local_body_object = LocalBodySerializer(source="local_body", read_only=True)
    district_object = DistrictSerializer(source="district", read_only=True)
    state_object = StateSerializer(source="state", read_only=True)
    disease_status = ChoiceField(choices=DISEASE_STATUS_CHOICES, default=DiseaseStatusEnum.SUSPECTED.value)

    class Meta:
        model = PatientRegistration
        exclude = ("created_by", "deleted", "ongoing_medication", "patient_search_id", "year_of_birth")
        read_only = TIMESTAMP_FIELDS


class PatientDetailSerializer(PatientListSerializer):
    class MedicalHistorySerializer(serializers.Serializer):
        disease = ChoiceField(choices=DISEASE_CHOICES)
        details = serializers.CharField(required=False, allow_blank=True)

    class PatientTeleConsultationSerializer(serializers.ModelSerializer):
        class Meta:
            model = PatientTeleConsultation
            fields = "__all__"

    phone_number = PhoneNumberField()
    facility = serializers.IntegerField(source="facility_id", allow_null=True, required=False)
    medical_history = serializers.ListSerializer(child=MedicalHistorySerializer(), required=False)

    tele_consultation_history = serializers.ListSerializer(child=PatientTeleConsultationSerializer(), read_only=True)
    last_consultation = serializers.SerializerMethodField(read_only=True)
    facility_object = FacilitySerializer(source="facility", read_only=True)

    disease_status = ChoiceField(choices=DISEASE_STATUS_CHOICES, default=DiseaseStatusEnum.SUSPECTED.value)

    class Meta:
        model = PatientRegistration
        exclude = ("created_by", "deleted", "patient_search_id", "year_of_birth")
        read_only = TIMESTAMP_FIELDS

    def get_last_consultation(self, obj):
        last_consultation = PatientConsultation.objects.filter(patient=obj).last()
        if not last_consultation:
            return None
        return PatientConsultationSerializer(last_consultation).data

    def validate_facility(self, value):
        if value is not None and Facility.objects.filter(id=value).first() is None:
            raise serializers.ValidationError("facility not found")
        return value

    def create(self, validated_data):
        with transaction.atomic():
            medical_history = validated_data.pop("medical_history", [])
            validated_data["created_by"] = self.context["request"].user
            patient = super().create(validated_data)
            diseases = []
            for disease in medical_history:
                diseases.append(Disease(patient=patient, **disease))
            if diseases:
                Disease.objects.bulk_create(diseases, ignore_conflicts=True)
            return patient

    def update(self, instance, validated_data):
        with transaction.atomic():
            medical_history = validated_data.pop("medical_history", [])
            patient = super().update(instance, validated_data)
            Disease.objects.filter(patient=patient).update(deleted=True)
            diseases = []
            for disease in medical_history:
                diseases.append(Disease(patient=patient, **disease))
            if diseases:
                Disease.objects.bulk_create(diseases, ignore_conflicts=True)
            return patient


class FacilityPatientStatsHistorySerializer(serializers.ModelSerializer):
    entry_date = serializers.DateField(default=make_aware(datetime.datetime.today()).date())

    class Meta:
        model = FacilityPatientStatsHistory
        exclude = ("deleted",)
        read_only_fields = (
            "id",
            "facility",
        )

    def create(self, validated_data):
        instance, _ = FacilityPatientStatsHistory.objects.update_or_create(
            facility=validated_data["facility"],
            entry_date=validated_data["entry_date"],
            defaults={**validated_data, "deleted": False},
        )
        return instance


class PatientSearchSerializer(serializers.ModelSerializer):
    gender = ChoiceField(choices=GENDER_CHOICES)
    phone_number = PhoneNumberField()

    class Meta:
        model = PatientSearch
        fields = "__all__"
