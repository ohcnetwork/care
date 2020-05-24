from django.utils.translation import ugettext as _
from rest_framework import serializers as rest_serializers
from rest_framework import exceptions as rest_exceptions
from apps.patients import models as patient_models
from apps.facility import models as facility_models


class PatientClinicalStatusSerializer(rest_serializers.ModelSerializer):
    class Meta:
        model = patient_models.PatientClinicalStatus
        fields = (
            "patient",
            "clinical",
        )
        read_only_fields = ("patient",)


class PatientCovidStatusSerializer(rest_serializers.ModelSerializer):
    class Meta:
        model = patient_models.PatientCovidStatus
        fields = (
            "patient",
            "covid",
        )
        read_only_fields = ("patient",)


class PatientFacilitySerializer(rest_serializers.ModelSerializer):
    class Meta:
        model = patient_models.PatientFacility
        fields = (
            "patient",
            "status",
            "facility",
            "patient_facility_id",
        )
        read_only_fields = (
            "patient",
            "facility",
        )


class PatientSerializer(rest_serializers.ModelSerializer):
    clinicals = PatientClinicalStatusSerializer(
        source="patientclinicalstatus_set", many=True
    )
    patient_facility = PatientFacilitySerializer(
        source="patientfacility_set", many=True
    )
    covids = PatientCovidStatusSerializer(source="patientcovidstatus_set", many=True)

    class Meta:
        model = patient_models.Patient
        fields = (
            "id",
            "facility",
            "nearest_facility",
            "name",
            "year",
            "month",
            "gender",
            "phone_number",
            "address",
            "date_of_birth",
            "year_of_birth",
            "nationality",
            "passport_no",
            "aadhar_no",
            "is_medical_worker",
            "blood_group",
            "contact_with_confirmed_carrier",
            "state",
            "district",
            "contact_with_suspected_carrier",
            "estimated_contact_date",
            "past_travel",
            "is_active",
            "countries_travelled_old",
            "countries_travelled",
            "date_of_return",
            "present_health",
            "ongoing_medication",
            "has_SARI",
            "local_body",
            "number_of_aged_dependents",
            "created_by",
            "number_of_chronic_diseased_dependents",
            "patient_search_id",
            "date_of_receipt_of_information",
            "cluster_group",
            "clinical_status_updated_at",
            "portea_called_at",
            "portea_able_to_connect",
            "symptoms",
            "diseases",
            "clinicals",
            "covids",
            "patient_facility",
            "home_isolation",
        )
        extra_kwargs = {
            "facility": {"required": True},
            "nearest_facility": {"required": True},
            "state": {"required": True},
            "district": {"required": True},
        }
        read_only_fields = (
            "symptoms",
            "diseases",
        )

    def create(self, validated_data):
        patient_status = validated_data.pop("patientfacility_set")
        clinicals = validated_data.pop("patientclinicalstatus_set")
        covids = validated_data.pop("patientcovidstatus_set")
        instance = super(PatientSerializer, self).create(validated_data)
        patient_models.PatientFacility.objects.bulk_create(
            [
                patient_models.PatientFacility(
                    **status, facility=validated_data["facility"], patient=instance
                )
                for status in patient_status
            ]
        )
        patient_models.PatientCovidStatus.objects.bulk_create(
            [
                patient_models.PatientCovidStatus(**covid, patient=instance)
                for covid in covids
            ]
        )
        patient_models.PatientClinicalStatus.objects.bulk_create(
            [
                patient_models.PatientClinicalStatus(**clinical, patient=instance)
                for clinical in clinicals
            ]
        )
        return instance


class PatientGroupSerializer(rest_serializers.ModelSerializer):
    class Meta:
        model = patient_models.PatientGroup
        fields = (
            "id",
            "name",
            "description",
            "created_at",
        )
        read_only_fields = ("created_at",)


class CovidStatusSerializer(rest_serializers.ModelSerializer):
    class Meta:
        model = patient_models.CovidStatus
        fields = (
            "id",
            "name",
            "description",
        )


class ClinicalStatusSerializer(rest_serializers.ModelSerializer):
    class Meta:
        model = patient_models.ClinicalStatus
        fields = (
            "id",
            "name",
            "description",
        )


class StatusSerializer(rest_serializers.ModelSerializer):
    class Meta:
        model = patient_models.Status
        fields = (
            "id",
            "name",
            "description",
        )
