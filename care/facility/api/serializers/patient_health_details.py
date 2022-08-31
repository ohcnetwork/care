from django.forms import ChoiceField
from care.facility.models.facility import Facility
from care.facility.models.patient_base import BLOOD_GROUP_CHOICES
from rest_framework import serializers
from care.facility.models import (
    PatientHealthDetails,
    PatientRegistration,
    PatientConsultation,
)
from care.facility.api.serializers.facility import FacilityBasicInfoSerializer
from care.utils.serializer.external_id_field import ExternalIdSerializerField


class PatientHealthDetailsSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="external_id", read_only=True)

    patient = ExternalIdSerializerField(queryset=PatientRegistration.objects.all())
    facility = ExternalIdSerializerField(queryset=Facility.objects.all())
    facility_object = FacilityBasicInfoSerializer(source="facility", read_only=True)
    created_in_consultation = ExternalIdSerializerField(
        queryset=PatientConsultation.objects.all(), required=False
    )
    blood_group = ChoiceField(choices=BLOOD_GROUP_CHOICES, required=True)

    class Meta:
        model = PatientHealthDetails
        exclude = ("deleted", "external_id")
