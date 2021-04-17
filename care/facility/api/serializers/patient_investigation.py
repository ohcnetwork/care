from django.db.models import fields
from rest_framework import serializers
from care.facility.models.patient_investigation import (
    InvestigationValue,
    PatientInvestigationGroup,
    PatientInvestigation,
    InvestigationSession,
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


class MinimalPatientInvestigationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientInvestigation
        exclude = TIMESTAMP_FIELDS + ("id", "groups")


class PatientInvestigationSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvestigationSession
        fields = ("external_id", "created_date")


class InvestigationValueSerializer(serializers.ModelSerializer):

    id = serializers.CharField(source="external_id", read_only=True)

    group_object = PatientInvestigationGroupSerializer(read_only=True)
    investigation_object = MinimalPatientInvestigationSerializer(read_only=True)
    session_object = PatientInvestigationSessionSerializer(source="session")

    class Meta:
        model = InvestigationValue
        read_only_fields = TIMESTAMP_FIELDS + ("session_id",)
        exclude = TIMESTAMP_FIELDS + ("external_id", "consultation")
