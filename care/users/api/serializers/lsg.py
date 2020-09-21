from rest_framework import serializers

from care.users.models import District, LocalBody, State, Ward


class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = "__all__"


class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = "__all__"


class LocalBodySerializer(serializers.ModelSerializer):
    class Meta:
        model = LocalBody
        fields = "__all__"


class WardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ward
        fields = "__all__"
