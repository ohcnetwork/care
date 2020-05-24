from django.utils.translation import ugettext as _
from rest_framework import serializers as rest_serializers
from rest_framework import exceptions as rest_exceptions
from apps.patients import models as patient_models
from apps.facility import models as facility_models


class PatientFacilitySerializer(rest_serializers.ModelSerializer):
    class Meta:
        model = patient_models.PatientFacility
        fields = (
            "patient_status",
            "facility",
            "patient_facility_id",
        )
        read_only_fields = ("facility",)


class PatientSerializer(rest_serializers.ModelSerializer):
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
            "covid_status",
            "current_facility",
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


class PatientStatusSerializer(rest_serializers.ModelSerializer):
    class Meta:
        model = patient_models.PatientStatus
        fields = (
            "id",
            "name",
            "description",
        )
