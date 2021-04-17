from rest_framework import serializers
from care.facility.models.patient_investigation import (
    InvestigationValue,
    PatientInvestigationGroup,
    PatientInvestigation,
)
from care.facility.api.serializers import TIMESTAMP_FIELDS


class PatientInvestigationGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientInvestigationGroup
        exclude = TIMESTAMP_FIELDS + ("id",)


class PatientInvestigationSerializer(serializers.ModelSerializer):

    groups = PatientInvestigationGroupSerializer(many=True)

    class Meta:
        model = PatientInvestigation
        exclude = TIMESTAMP_FIELDS + ("id",)


class InvestigationValueSerializer(serializers.ModelSerializer):

    group = PatientInvestigationGroupSerializer()
    test = PatientInvestigationSerializer()

    class Meta:
        model = InvestigationValue
        read_only_fields = TIMESTAMP_FIELDS
        exclude = TIMESTAMP_FIELDS + ("id",)
