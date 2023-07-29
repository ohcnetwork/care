# ModelSerializer
from rest_framework import serializers

from care.abdm.models import AbhaNumber


class AbhaNumberSerializer(serializers.ModelSerializer):
    class Meta:
        model = AbhaNumber
        exclude = ("access_token", "refresh_token", "txn_id")
