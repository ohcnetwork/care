from rest_framework import serializers

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.models.patient_sample import PatientSample, PatientSampleFlow
from config.serializers import ChoiceField


class PatientSampleFlowSerializer(serializers.ModelSerializer):
    status = ChoiceField(choices=PatientSample.SAMPLE_TEST_FLOW_CHOICES, required=False)

    class Meta:
        model = PatientSampleFlow
        fields = "__all__"


class PatientSampleSerializer(serializers.ModelSerializer):
    status = ChoiceField(choices=PatientSample.SAMPLE_TEST_FLOW_CHOICES, required=False)
    result = ChoiceField(choices=PatientSample.SAMPLE_TEST_RESULT_CHOICES, required=False)
    notes = serializers.CharField(required=False)
    date_of_sample = serializers.DateTimeField(read_only=True)
    date_of_result = serializers.DateTimeField(read_only=True)

    class Meta:
        model = PatientSample
        exclude = TIMESTAMP_FIELDS + ("patient",)


class PatientSampleDetailSerializer(PatientSampleSerializer):
    flow = serializers.ListSerializer(child=PatientSampleFlowSerializer())
