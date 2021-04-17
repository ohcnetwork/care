from rest_framework import serializers
from care.facility.models.patient_test import TestValue, TestGroup, PatientTest
from care.facility.api.serializers import TIMESTAMP_FIELDS


class TestGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestGroup
        read_only_fields = TIMESTAMP_FIELDS
        exclude = TIMESTAMP_FIELDS + ("id",)


class PatientTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientTest
        read_only_fields = TIMESTAMP_FIELDS
        exclude = TIMESTAMP_FIELDS + ("id",)
        required_fields = [
            "name",
            "group",
            "unit",
            "type"
        ]
        extra_kwargs = {i: {'required': True} for i in required_fields}


class TestValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestValue
        read_only_fields = TIMESTAMP_FIELDS
        exclude = TIMESTAMP_FIELDS + ("id",)
