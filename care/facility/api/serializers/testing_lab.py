from rest_framework import serializers

from care.facility.models.testing_lab import TestingLab
from care.utils.serializer.phonenumber_ispossible_field import PhoneNumberIsPossibleField


class TestingLabSerializer(serializers.ModelSerializer):
    phone_number = PhoneNumberIsPossibleField()

    class Meta:
        model = TestingLab
        exclude = ("created_by",)
