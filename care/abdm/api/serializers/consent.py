from rest_framework import serializers

from care.abdm.models.consent import Consent
from care.users.api.serializers.user import UserBaseMinimumSerializer


class ConsentSerializer(serializers.ModelSerializer):
    requester = UserBaseMinimumSerializer(read_only=True)

    class Meta:
        model = Consent
        exclude = ("deleted",)
