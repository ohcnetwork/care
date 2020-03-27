from rest_framework import serializers

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.models import PatientSample


class PatientSampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientSample
        exclude = TIMESTAMP_FIELDS
