from django.db import models
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import (
    CharField,
    FloatField,
    JSONField,
    ModelSerializer,
    UUIDField,
)

from care.facility.api.serializers.patient_consultation import (
    PatientConsultationSerializer,
)
from care.facility.models.patient_consultation import PatientConsultation
from care.hcx.api.serializers.policy import PolicySerializer
from care.hcx.models.base import (
    CLAIM_TYPE_CHOICES,
    OUTCOME_CHOICES,
    PRIORITY_CHOICES,
    STATUS_CHOICES,
    USE_CHOICES,
)
from care.hcx.models.claim import Claim
from care.hcx.models.json_schema.claim import ITEMS
from care.hcx.models.policy import Policy
from care.users.api.serializers.user import UserBaseMinimumSerializer
from care.utils.models.validators import JSONFieldSchemaValidator
from config.serializers import ChoiceField

TIMESTAMP_FIELDS = (
    "created_date",
    "modified_date",
)


class ClaimSerializer(ModelSerializer):
    # TODO Remove when #5492 is completed
    id = UUIDField(source="external_id", read_only=True)

    consultation = UUIDField(write_only=True, required=True)
    consultation_object = PatientConsultationSerializer(
        source="consultation", read_only=True
    )

    policy = UUIDField(write_only=True, required=True)
    policy_object = PolicySerializer(source="policy", read_only=True)

    items = JSONField(required=False, validators=[JSONFieldSchemaValidator(ITEMS)])
    total_claim_amount = FloatField(required=False)
    total_amount_approved = FloatField(required=False)

    use = ChoiceField(choices=USE_CHOICES, default="claim")
    status = ChoiceField(choices=STATUS_CHOICES, default="active")
    priority = ChoiceField(choices=PRIORITY_CHOICES, default="normal")
    type = ChoiceField(choices=CLAIM_TYPE_CHOICES, default="institutional")

    outcome = ChoiceField(choices=OUTCOME_CHOICES, read_only=True)
    error_text = CharField(read_only=True)

    created_by = UserBaseMinimumSerializer(read_only=True)
    last_modified_by = UserBaseMinimumSerializer(read_only=True)

    class Meta:
        model = Claim
        exclude = ("deleted", "external_id")
        read_only_fields = TIMESTAMP_FIELDS

    def validate(self, attrs):
        if "consultation" in attrs and "policy" in attrs:
            consultation = get_object_or_404(
                PatientConsultation.objects.filter(external_id=attrs["consultation"])
            )
            policy = get_object_or_404(
                Policy.objects.filter(external_id=attrs["policy"])
            )
            attrs["consultation"] = consultation
            attrs["policy"] = policy
        else:
            raise ValidationError(
                {"consultation": "Field is Required", "policy": "Field is Required"}
            )

        if "total_claim_amount" not in attrs and "items" in attrs:
            total_claim_amount = 0.0
            for item in attrs["items"]:
                total_claim_amount += item["price"]

            attrs["total_claim_amount"] = total_claim_amount

        return super().validate(attrs)

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        validated_data["last_modified_by"] = self.context["request"].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        instance.last_modified_by = self.context["request"].user
        return super().update(instance, validated_data)


class BareMinimumPolicyClaimSerializer(ModelSerializer):
    id = UUIDField(source="external_id", read_only=True)
    subscriber_id = models.TextField(null=True, blank=True)
    policy_id = models.TextField(null=True, blank=True)

    insurer_id = models.TextField(null=True, blank=True)
    insurer_name = models.TextField(null=True, blank=True)

    class Meta:
        model = Policy
        fields = [
            "id",
            "created_date",
            "modified_date",
            "subscriber_id",
            "policy_id",
            "insurer_id",
            "insurer_name",
        ]
        read_only_fields = TIMESTAMP_FIELDS


class ClaimListSerializer(ModelSerializer):
    id = UUIDField(source="external_id", read_only=True)
    outcome = ChoiceField(choices=OUTCOME_CHOICES, read_only=True)
    error_text = CharField(read_only=True)
    policy_object = BareMinimumPolicyClaimSerializer(source="policy", read_only=True)
    use = ChoiceField(choices=USE_CHOICES, default="claim")
    items = JSONField(required=False, validators=[JSONFieldSchemaValidator(ITEMS)])
    total_claim_amount = FloatField(required=False)

    class Meta:
        model = Claim
        fields = [
            "id",
            "outcome",
            "error_text",
            "created_date",
            "use",
            "policy_object",
            "items",
            "total_claim_amount",
            "error_text",
            "created_date",
            "modified_date",
        ]
        read_only_fields = TIMESTAMP_FIELDS


class ClaimDetailSerializer(ClaimListSerializer):
    consultation = UUIDField(write_only=True, required=True)
    consultation_object = PatientConsultationSerializer(
        source="consultation", read_only=True
    )

    policy = UUIDField(write_only=True, required=True)
    policy_object = PolicySerializer(source="policy", read_only=True)

    total_amount_approved = FloatField(required=False)

    status = ChoiceField(choices=STATUS_CHOICES, default="active")
    priority = ChoiceField(choices=PRIORITY_CHOICES, default="normal")
    type = ChoiceField(choices=CLAIM_TYPE_CHOICES, default="institutional")
    created_by = UserBaseMinimumSerializer(read_only=True)
    last_modified_by = UserBaseMinimumSerializer(read_only=True)

    class Meta:
        model = Claim
        exclude = ("deleted", "external_id")
        read_only_fields = TIMESTAMP_FIELDS

    def validate(self, attrs):
        if "consultation" in attrs and "policy" in attrs:
            consultation = get_object_or_404(
                PatientConsultation.objects.filter(external_id=attrs["consultation"])
            )
            policy = get_object_or_404(
                Policy.objects.filter(external_id=attrs["policy"])
            )
            attrs["consultation"] = consultation
            attrs["policy"] = policy
        else:
            raise ValidationError(
                {"consultation": "Field is Required", "policy": "Field is Required"}
            )

        if "total_claim_amount" not in attrs and "items" in attrs:
            total_claim_amount = 0.0
            for item in attrs["items"]:
                total_claim_amount += item["price"]

            attrs["total_claim_amount"] = total_claim_amount

        return super().validate(attrs)

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        validated_data["last_modified_by"] = self.context["request"].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        instance.last_modified_by = self.context["request"].user
        return super().update(instance, validated_data)
