from rest_framework import serializers

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.models import HospitalDoctors


class HospitalDoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = HospitalDoctors
        read_only_fields = ('id',)
        exclude = TIMESTAMP_FIELDS + ("facility",)
