from rest_framework import serializers
from rest_framework.fields import ChoiceField

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.models.patient_sample import SAMPLE_TEST_FLOW_CHOICES, PatientSample, PatientSampleFlow


class PatientSampleFlowSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientSampleFlow
        fields = "__all__"


class PatientSampleSerializer(serializers.ModelSerializer):
    status = ChoiceField(choices=SAMPLE_TEST_FLOW_CHOICES)
    notes = serializers.CharField(required=False)

    class Meta:
        model = PatientSample
        exclude = TIMESTAMP_FIELDS


class PatientSampleDetailSerializer(PatientSampleSerializer):
    flow = serializers.ListSerializer(child=PatientSampleFlowSerializer())
