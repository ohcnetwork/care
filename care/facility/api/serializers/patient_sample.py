from rest_framework import serializers

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.models import PatientSample, PatientSampleFlow


class PatientSampleFlowSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientSampleFlow
        fields = "__all__"


class PatientSampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientSample
        exclude = TIMESTAMP_FIELDS


class PatientSampleDetailSerializer(PatientSampleSerializer):
    flow = serializers.ListSerializer(child=PatientSampleFlowSerializer())
