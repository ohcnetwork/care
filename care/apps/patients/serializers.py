from rest_framework import serializers
from django.utils.translation import ugettext as _
from rest_framework import serializers as rest_serializers

from apps.patients import models as patient_models
from apps.facility import models as facility_models


class PatientSerializer(rest_serializers.ModelSerializer):
    class Meta:
        model = patient_models.Patient
        fields = (
            "id",
            "facility",
            "nearest_facility",
            "meta_info",
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
            "disease_status",
            "number_of_aged_dependents",
            "created_by",
            "number_of_chronic_diseased_dependents",
            "patient_search_id",
            "date_of_receipt_of_information",
            "clinical_status_updated_at",
            "portea_called_at",
            "portea_able_to_connect"
        )
        extra_kwargs = {
            "facility": {"required": True},
            "nearest_facility": {"required": True},
            "state": {"required": True},
            "district": {"required": True},
        }
