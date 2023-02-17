from rest_framework.serializers import (
    ModelSerializer,
    UUIDField,
    CharField,
    JSONField,
    FloatField,
)
from config.serializers import ChoiceField
from care.hcx.models.claim import Claim
from care.hcx.models.policy import Policy
from care.hcx.api.serializers.policy import PolicySerializer
from care.hcx.models.base import (
    STATUS_CHOICES,
    PRIORITY_CHOICES,
    USE_CHOICES,
    CLAIM_TYPE_CHOICES,
    OUTCOME_CHOICES,
)
from django.shortcuts import get_object_or_404
from care.facility.models.patient_consultation import PatientConsultation
from care.facility.api.serializers.patient_consultation import (
    PatientConsultationSerializer,
)
from rest_framework.exceptions import ValidationError
from care.utils.models.validators import JSONFieldSchemaValidator
from care.hcx.models.json_schema.claim import PROCEDURES
from care.users.api.serializers.user import UserBaseMinimumSerializer

TIMESTAMP_FIELDS = (
    "created_date",
    "modified_date",
)


class ClaimSerializer(ModelSerializer):
    id = UUIDField(source="external_id", read_only=True)

    consultation = UUIDField(write_only=True, required=True)
    consultation_object = PatientConsultationSerializer(
        source="consultation", read_only=True
    )

    policy = UUIDField(write_only=True, required=True)
    policy_object = PolicySerializer(source="policy", read_only=True)

    procedures = JSONField(
        required=False, validators=[JSONFieldSchemaValidator(PROCEDURES)]
    )
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

        if "total_claim_amount" not in attrs and "procedures" in attrs:
            total_claim_amount = 0.0
            for procedure in attrs["procedures"]:
                total_claim_amount += procedure["price"]

            attrs["total_claim_amount"] = total_claim_amount

        return super().validate(attrs)

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        validated_data["last_modified_by"] = self.context["request"].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        instance.last_modified_by = self.context["request"].user
        return super().update(instance, validated_data)
