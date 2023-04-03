from rest_framework.serializers import UUIDField, Serializer
from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from care.hcx.models.policy import Policy
from care.hcx.models.claim import Claim


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
