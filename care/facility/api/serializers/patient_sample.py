import datetime

from django.utils.timezone import make_aware
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.models.patient_sample import PatientSample, PatientSampleFlow
from config.serializers import ChoiceField


class PatientSampleFlowSerializer(serializers.ModelSerializer):
    status = ChoiceField(choices=PatientSample.SAMPLE_TEST_FLOW_CHOICES, required=False)

    class Meta:
        model = PatientSampleFlow
        fields = "__all__"


class PatientSampleSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    result = serializers.CharField(read_only=True)
    notes = serializers.CharField(required=False)
    date_of_sample = serializers.DateTimeField(read_only=True)
    date_of_result = serializers.DateTimeField(read_only=True)
    patient_id = serializers.IntegerField(required=False)
    consultation_id = serializers.IntegerField(required=False)

    class Meta:
        model = PatientSample
        exclude = TIMESTAMP_FIELDS + ("patient", "consultation")

    def create(self, validated_data):
        return super(PatientSampleSerializer, self).create(validated_data)


class PatientSamplePatchSerializer(PatientSampleSerializer):
    status = ChoiceField(choices=PatientSample.SAMPLE_TEST_FLOW_CHOICES)
    result = ChoiceField(choices=PatientSample.SAMPLE_TEST_RESULT_CHOICES, required=False)

    def update(self, instance, validated_data):
        try:
            choice = PatientSample.SAMPLE_TEST_FLOW_CHOICES[validated_data["status"] - 1][1]
        except KeyError:
            raise ValidationError({"status": ["is required"]})
        valid_choices = PatientSample.SAMPLE_FLOW_RULES[PatientSample.SAMPLE_TEST_FLOW_CHOICES[instance.status - 1][1]]
        if choice not in valid_choices:
            raise ValidationError({"status": [f"Next valid choices are: {', '.join(valid_choices)}"]})
        if choice != "COMPLETED" and validated_data.get("result"):
            raise ValidationError({"result": [f"Result can't be updated unless test is complete"]})
        if choice == "COMPLETED" and not validated_data.get("result"):
            raise ValidationError({"result": [f"is required as the test is complete"]})

        if validated_data.get("status") == PatientSample.SAMPLE_TEST_FLOW_MAP["SENT_TO_COLLECTON_CENTRE"]:
            validated_data["date_of_sample"] = make_aware(datetime.datetime.now())
        elif validated_data.get("status") == PatientSample.SAMPLE_TEST_FLOW_MAP["DENIED"]:
            validated_data["result"] = PatientSample.SAMPLE_TEST_RESULT_MAP["INVALID"]
        elif validated_data.get("status") == PatientSample.SAMPLE_TEST_FLOW_MAP["REQUEST_SUBMITTED"]:
            validated_data["result"] = PatientSample.SAMPLE_TEST_RESULT_MAP["AWAITING"]
        elif validated_data.get("result") is not None:
            validated_data["date_of_result"] = make_aware(datetime.datetime.now())

        return super().update(instance, validated_data)


class PatientSampleReadSerializer(PatientSamplePatchSerializer):
    flow = serializers.ListSerializer(child=PatientSampleFlowSerializer())
    patient_name = serializers.CharField(source="patient.name")
