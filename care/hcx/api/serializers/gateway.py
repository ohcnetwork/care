from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import Serializer, UUIDField

from care.hcx.models.claim import Claim
from care.hcx.models.communication import Communication
from care.hcx.models.policy import Policy


class CheckEligibilitySerializer(Serializer):
    policy = UUIDField(required=True)

    def validate(self, attrs):
        if "policy" in attrs:
            get_object_or_404(Policy.objects.filter(external_id=attrs["policy"]))
        else:
            raise ValidationError({"policy": "Field is Required"})

        return super().validate(attrs)


class MakeClaimSerializer(Serializer):
    claim = UUIDField(required=True)

    def validate(self, attrs):
        if "claim" in attrs:
            get_object_or_404(Claim.objects.filter(external_id=attrs["claim"]))
        else:
            raise ValidationError({"claim": "Field is Required"})

        return super().validate(attrs)


class SendCommunicationSerializer(Serializer):
    communication = UUIDField(required=True)

    def validate(self, attrs):
        if "communication" in attrs:
            get_object_or_404(
                Communication.objects.filter(external_id=attrs["communication"])
            )
        else:
            raise ValidationError({"communication": "Field is Required"})

        return super().validate(attrs)
