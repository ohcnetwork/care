from care.facility.models.investigation import Investigation
from rest_framework import serializers
from config.serializers import ChoiceField
from care.facility.models.patient_base import BLOOD_GROUP_CHOICES
from care.facility.api.serializers import TIMESTAMP_FIELDS


class InvestigationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Investigation
        read_only_fields = TIMESTAMP_FIELDS
        exclude = TIMESTAMP_FIELDS + ("id",)
        required_fields = [
            "consultation",
            "investigation_data"
        ]
