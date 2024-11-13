from rest_framework import serializers

from care.users.models import PlugConfig


class PlugConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlugConfig
        exclude = ("id",)
