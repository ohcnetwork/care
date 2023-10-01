from rest_framework import serializers

from care.abdm.models.consent import ConsentRequest
from care.users.api.serializers.user import UserBaseMinimumSerializer


class ConsentRequestSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="external_id", read_only=True)
    requester = UserBaseMinimumSerializer(read_only=True)

    class Meta:
        model = ConsentRequest
        exclude = ("deleted", "external_id")
