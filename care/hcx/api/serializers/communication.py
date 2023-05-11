from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import CharField, JSONField, ModelSerializer, UUIDField

from care.hcx.api.serializers.claim import ClaimSerializer
from care.hcx.models.claim import Claim
from care.hcx.models.communication import Communication
from care.users.api.serializers.user import UserBaseMinimumSerializer

TIMESTAMP_FIELDS = (
    "created_date",
    "modified_date",
)


class CommunicationSerializer(ModelSerializer):
    id = UUIDField(source="external_id", read_only=True)

    claim = UUIDField(write_only=True, required=True)
    claim_object = ClaimSerializer(source="claim", read_only=True)

    identifier = CharField(required=False)
    content = JSONField(required=False)

    created_by = UserBaseMinimumSerializer(read_only=True)
    last_modified_by = UserBaseMinimumSerializer(read_only=True)

    class Meta:
        model = Communication
        exclude = ("deleted", "external_id")
        read_only_fields = TIMESTAMP_FIELDS

    def validate(self, attrs):
        if "claim" in attrs:
            claim = get_object_or_404(Claim.objects.filter(external_id=attrs["claim"]))
            attrs["claim"] = claim
        else:
            raise ValidationError({"claim": "Field is Required"})

        return super().validate(attrs)

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        validated_data["last_modified_by"] = self.context["request"].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        instance.last_modified_by = self.context["request"].user
        return super().update(instance, validated_data)
