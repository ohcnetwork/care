from rest_framework import serializers

from care.facility.models import GENDER_CHOICES, PatientSearch
from care.facility.api.serializers.facility import FacilityBasicInfoSerializer

from config.serializers import ChoiceField


class PatientScopedSearchSerializer(serializers.ModelSerializer):

    gender = ChoiceField(choices=GENDER_CHOICES)
    facility = FacilityBasicInfoSerializer()

    class Meta:
        model = PatientSearch
        exclude = ("patient_id",)
