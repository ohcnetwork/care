from rest_framework import serializers as rest_serializers

from apps.patients import models as patients_models


class PatientTimeLineSerializer(rest_serializers.ModelSerializer):

    class Meta:
        model = patients_models.PatientTimeLine
        fields = ('date', 'description',)
