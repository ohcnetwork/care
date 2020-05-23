from rest_framework import serializers
from django.utils.translation import ugettext as _
from rest_framework import serializers as rest_serializers

from apps.patients import models as patient_models
from apps.facility import models as facility_models


class PatientSerializer(rest_serializers.ModelSerializer):

    class Meta:
        model = patient_models.Patient
        fields = ("id", "facility", "nearest_facility", "meta_info", "name", "age", "gender", "phone_number", "address", "date_of_birth", "year_of_birth", "nationality", "passport_no", "aadhar_no", "is_medical_worker", "blood_group", "contact_with_confirmed_carrier", "contact_with_suspected_carrier", "estimated_contact_date", "past_travel",
                  "countries_travelled_old", "countries_travelled", "date_of_return", "present_health", "ongoing_medication", "has_SARI", "local_body", "district", "state", "disease_status", "number_of_aged_dependents", "number_of_chronic_diseased_dependents", "created_by", "is_active", "patient_search_id", "date_of_receipt_of_information",)
        extra_kwargs = {
            'aaadhar_no': {'required': True},
            'facility': {'required': True},
            'nearest_facility': {'required': True},
            'age': {'required': True},
            'blood_group': {'required': True},
            'sirsa':{'required': True},
            'district':{'required': True},
        }        
