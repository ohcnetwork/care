from rest_framework import serializers

from care.facility.models import GENDER_CHOICES, PatientSearch
from care.facility.api.serializers.facility import FacilityBasicInfoSerializer

from config.serializers import ChoiceField


class PatientScopedSearchSerializer(serializers.ModelSerializer):

    gender = ChoiceField(choices=GENDER_CHOICES)
    facility = FacilityBasicInfoSerializer()
    id = serializers.CharField(source="patient_external_id")

    class Meta:
        model = PatientSearch
        exclude = ("patient_id", "external_id")
