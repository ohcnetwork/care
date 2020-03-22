from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from care.facility.models import FACILITY_TYPES, AmbulanceDriver
from care.facility.models import Facility, Ambulance
from config.serializers import ChoiceField

User = get_user_model()

TIMESTAMP_FIELDS = ('created_date', 'modified_date', 'deleted',)


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


class AmbulanceDriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = AmbulanceDriver
        exclude = TIMESTAMP_FIELDS + ('ambulance',)


class AmbulanceSerializer(serializers.ModelSerializer):
    drivers = serializers.ListSerializer(
        child=AmbulanceDriverSerializer())

    class Meta:
        model = Ambulance
        exclude = TIMESTAMP_FIELDS

    def create(self, validated_data):
        with transaction.atomic():
            drivers = validated_data.pop('drivers', [])
            ambulance = super(AmbulanceSerializer, self).create(validated_data)
            for d in drivers:
                d['ambulance'] = ambulance
                AmbulanceDriverSerializer().create(d)
            return ambulance

    def update(self, instance, validated_data):
        drivers = validated_data.pop('drivers', [])
        ambulance = super(AmbulanceSerializer, self).create(validated_data)
        return ambulance
