from rest_framework import serializers

from care.facility.models.testing_lab import TestingLab


class TestingLabSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestingLab
        exclude = ("created_by",)
