from django.contrib.auth import get_user_model
from rest_framework import serializers

from care.facility.models import FACILITY_TYPES, AmbulanceDriver
from care.facility.models import Facility, Ambulance
from config.serializers import ChoiceField

User = get_user_model()

READ_ONLY_FIELDS = ('created_date', 'modified_date', 'deleted',)


class FacilitySerializer(serializers.ModelSerializer):
    """Serializer for facility.models.Facility."""

    district = ChoiceField(choices=User.DISTRICT_CHOICES)
    facility_type = ChoiceField(choices=FACILITY_TYPES)

    class Meta:
        model = Facility
        fields = [
            "id",
            "name",
            "district",
            "facility_type",
            "address",
            "phone_number",
        ]


class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = AmbulanceDriver
        fields = '__all__'
        read_only_fields = READ_ONLY_FIELDS


class AmbulanceSerializer(serializers.ModelSerializer):
    drivers = serializers.ListSerializer(child=DriverSerializer())

    class Meta:
        model = Ambulance
        fields = '__all__'
        read_only_fields = READ_ONLY_FIELDS
