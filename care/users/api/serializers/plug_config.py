from rest_framework import serializers

from care.users.models import PlugConfig


class PLugConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlugConfig
        exclude = ("id",)
