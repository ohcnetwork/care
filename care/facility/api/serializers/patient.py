import datetime

from django.db import transaction
from django.utils.timezone import make_aware
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
    PatientContactDetails,
    PatientMetaInfo,
    PatientRegistration,
    PatientSearch,
)
from care.facility.models.patient_base import DISEASE_STATUS_CHOICES, DiseaseStatusEnum, BLOOD_GROUP_CHOICES
from care.facility.models.patient_consultation import PatientConsultation
from care.facility.models.patient_tele_consultation import PatientTeleConsultation
from care.users.api.serializers.lsg import DistrictSerializer, LocalBodySerializer, StateSerializer
from care.utils.serializer.external_id_field import ExternalIdSerializerField
from care.utils.serializer.phonenumber_ispossible_field import PhoneNumberIsPossibleField
from config.serializers import ChoiceField


class PatientMetaInfoSerializer(serializers.ModelSerializer):
    occupation = ChoiceField(choices=PatientMetaInfo.OccupationChoices)

    class Meta:
        model = PatientMetaInfo
        fields = "__all__"


class PatientListSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="external_id", read_only=True)
    facility = serializers.UUIDField(source="facility.external_id", allow_null=True, read_only=True)
    facility_object = FacilityBasicInfoSerializer(source="facility", read_only=True)
    local_body_object = LocalBodySerializer(source="local_body", read_only=True)
    district_object = DistrictSerializer(source="district", read_only=True)
    state_object = StateSerializer(source="state", read_only=True)

    blood_group = ChoiceField(choices=BLOOD_GROUP_CHOICES, required=True)
    disease_status = ChoiceField(choices=DISEASE_STATUS_CHOICES, default=DiseaseStatusEnum.SUSPECTED.value)
    source = ChoiceField(choices=PatientRegistration.SourceChoices)

    class Meta:
        model = PatientRegistration
        exclude = (
            "created_by",
            "deleted",
            "ongoing_medication",
            "patient_search_id",
            "year_of_birth",
            "meta_info",
            "countries_travelled_old",
            "allergies",
            "external_id",
        )
        read_only = TIMESTAMP_FIELDS


class PatientContactDetailsSerializer(serializers.ModelSerializer):
    relation_with_patient = ChoiceField(choices=PatientContactDetails.RelationChoices)
    mode_of_contact = ChoiceField(choices=PatientContactDetails.ModeOfContactChoices)

    patient_in_contact_object = PatientListSerializer(read_only=True, source="patient_in_contact")
    patient_in_contact = serializers.UUIDField(source="patient_in_contact.external_id")

    class Meta:
        model = PatientContactDetails
        exclude = ("patient",)

    def validate_patient_in_contact(self, value):
        if value:
            value = PatientRegistration.objects.get(external_id=value)
        return value

    def to_internal_value(self, data):
        iv = super().to_internal_value(data)
        if iv.get("patient_in_contact"):
            iv["patient_in_contact"] = iv["patient_in_contact"]["external_id"]
        return iv


class PatientDetailSerializer(PatientListSerializer):
    class MedicalHistorySerializer(serializers.Serializer):
        disease = ChoiceField(choices=DISEASE_CHOICES)
        details = serializers.CharField(required=False, allow_blank=True)

    class PatientTeleConsultationSerializer(serializers.ModelSerializer):
        class Meta:
            model = PatientTeleConsultation
            fields = "__all__"

    phone_number = PhoneNumberIsPossibleField()
    facility = serializers.UUIDField(source="facility.external_id", allow_null=True, required=False)
    medical_history = serializers.ListSerializer(child=MedicalHistorySerializer(), required=False)

    tele_consultation_history = serializers.ListSerializer(child=PatientTeleConsultationSerializer(), read_only=True)
    last_consultation = serializers.SerializerMethodField(read_only=True)
    facility_object = FacilitySerializer(source="facility", read_only=True)
    nearest_facility_object = FacilitySerializer(source="nearest_facility", read_only=True)

    source = ChoiceField(choices=PatientRegistration.SourceChoices, default=PatientRegistration.SourceEnum.CARE.value)
    disease_status = ChoiceField(choices=DISEASE_STATUS_CHOICES, default=DiseaseStatusEnum.SUSPECTED.value)

    meta_info = PatientMetaInfoSerializer(required=False, allow_null=True)
    contacted_patients = PatientContactDetailsSerializer(many=True, required=False, allow_null=True)

    class Meta:
        model = PatientRegistration
        exclude = (
            "created_by",
            "deleted",
            "patient_search_id",
            "year_of_birth",
            "countries_travelled_old",
            "external_id",
        )
        include = ("contacted_patients",)
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

    def validate_countries_travelled(self, value):
        if not value:
            value = []
        if not isinstance(value, list):
            value = [value]
        return value

    def validate(self, attrs):
        validated = super().validate(attrs)
        if not self.partial and not validated.get("age") and not validated.get("date_of_birth"):
            raise serializers.ValidationError({"non_field_errors": [f"Either age or date_of_birth should be passed"]})
        return validated

    def create(self, validated_data):
        with transaction.atomic():
            medical_history = validated_data.pop("medical_history", [])
            meta_info = validated_data.pop("meta_info", {})
            contacted_patients = validated_data.pop("contacted_patients", [])

            if "facility" in validated_data:
                external_id = validated_data.pop("facility")["external_id"]
                if external_id:
                    validated_data["facility_id"] = Facility.objects.get(external_id=external_id).id

            validated_data["created_by"] = self.context["request"].user
            patient = super().create(validated_data)
            diseases = []

            for disease in medical_history:
                diseases.append(Disease(patient=patient, **disease))
            if diseases:
                Disease.objects.bulk_create(diseases, ignore_conflicts=True)

            if meta_info:
                meta_info_obj = PatientMetaInfo.objects.create(**meta_info)
                patient.meta_info = meta_info_obj
                patient.save()

            if contacted_patients:
                contacted_patient_objs = [PatientContactDetails(**data, patient=patient) for data in contacted_patients]
                PatientContactDetails.objects.bulk_create(contacted_patient_objs)

            return patient

    def update(self, instance, validated_data):
        with transaction.atomic():
            medical_history = validated_data.pop("medical_history", [])
            meta_info = validated_data.pop("meta_info", {})
            contacted_patients = validated_data.pop("contacted_patients", [])

            if "facility" in validated_data:
                external_id = validated_data.pop("facility")["external_id"]
                if external_id:
                    validated_data["facility_id"] = Facility.objects.get(external_id=external_id).id

            patient = super().update(instance, validated_data)
            Disease.objects.filter(patient=patient).update(deleted=True)
            diseases = []
            for disease in medical_history:
                diseases.append(Disease(patient=patient, **disease))
            if diseases:
                Disease.objects.bulk_create(diseases, ignore_conflicts=True)

            if meta_info:
                for key, value in meta_info.items():
                    setattr(patient.meta_info, key, value)
                patient.meta_info.save()

            if self.partial is not True:  # clear the list and enter details if PUT
                patient.contacted_patients.all().delete()

            if contacted_patients:
                contacted_patient_objs = [PatientContactDetails(**data, patient=patient) for data in contacted_patients]
                PatientContactDetails.objects.bulk_create(contacted_patient_objs)

            return patient


class FacilityPatientStatsHistorySerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="external_id", read_only=True)
    entry_date = serializers.DateField(default=make_aware(datetime.datetime.today()).date())
    facility = ExternalIdSerializerField(queryset=Facility.objects.all(), read_only=True)

    class Meta:
        model = FacilityPatientStatsHistory
        exclude = (
            "deleted",
            "external_id",
        )
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
    phone_number = PhoneNumberIsPossibleField()
    patient_id = serializers.UUIDField(source="external_id", read_only=True)
    # facility_id = serializers.UUIDField(read_only=True, allow_null=True)

    class Meta:
        model = PatientSearch
        exclude = ("date_of_birth", "year_of_birth", "external_id", "id") + TIMESTAMP_FIELDS


class PatientTransferSerializer(serializers.ModelSerializer):
    facility_object = FacilityBasicInfoSerializer(source="facility", read_only=True)
    facility = ExternalIdSerializerField(write_only=True, queryset=Facility.objects.all())
    patient = serializers.UUIDField(source="external_id", read_only=True)

    class Meta:
        model = PatientRegistration
        fields = ("facility", "date_of_birth", "patient", "facility_object")

    def validate_date_of_birth(self, value):
        if self.instance and self.instance.date_of_birth != value:
            raise serializers.ValidationError("Date of birth does not match")
        return value

    def create(self, validated_data):
        raise NotImplementedError

    def save(self, **kwargs):
        self.instance.facility = self.validated_data["facility"]
        self.instance.save()
