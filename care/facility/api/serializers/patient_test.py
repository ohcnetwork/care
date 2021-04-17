from rest_framework import serializers
from care.facility.models.patient_test import TestValue, PatientTestGroup, PatientTest
from care.facility.api.serializers import TIMESTAMP_FIELDS


class PatientTestGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientTestGroup
        exclude = TIMESTAMP_FIELDS + ("id",)


class PatientTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientTest
        exclude = TIMESTAMP_FIELDS + ("id",)


class TestValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestValue
        read_only_fields = TIMESTAMP_FIELDS
        exclude = TIMESTAMP_FIELDS + ("id",)
