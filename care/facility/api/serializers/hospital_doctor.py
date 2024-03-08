from rest_framework import serializers

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.models import DoctorTypes, HospitalDoctors
from config.serializers import ChoiceField


class HospitalDoctorSerializer(serializers.ModelSerializer):
    area_text = ChoiceField(choices=DoctorTypes.choices, read_only=True, source="area")
    id = serializers.UUIDField(source="external_id", read_only=True)

    class Meta:
        model = HospitalDoctors
        read_only_fields = (
            "id",
            "area_text",
        )
        exclude = TIMESTAMP_FIELDS + ("facility", "external_id")
