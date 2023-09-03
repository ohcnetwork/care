from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import CharField, ModelSerializer, UUIDField

from care.facility.api.serializers.patient import PatientDetailSerializer
from care.facility.models.patient import PatientRegistration
from care.hcx.models.policy import (
    OUTCOME_CHOICES,
    PRIORITY_CHOICES,
    PURPOSE_CHOICES,
    STATUS_CHOICES,
    Policy,
)
from care.users.api.serializers.user import UserBaseMinimumSerializer
from config.serializers import ChoiceField

TIMESTAMP_FIELDS = (
    "created_date",
    "modified_date",
)


class PolicySerializer(ModelSerializer):
    id = UUIDField(source="external_id", read_only=True)

    patient = UUIDField(write_only=True, required=True)
    patient_object = PatientDetailSerializer(source="patient", read_only=True)

    subscriber_id = CharField()
    policy_id = CharField()

    insurer_id = CharField(required=False)
    insurer_name = CharField(required=False)

    status = ChoiceField(choices=STATUS_CHOICES, default="active")
    priority = ChoiceField(choices=PRIORITY_CHOICES, default="normal")
    purpose = ChoiceField(choices=PURPOSE_CHOICES, default="benefits")

    outcome = ChoiceField(choices=OUTCOME_CHOICES, read_only=True)
    error_text = CharField(read_only=True)

    created_by = UserBaseMinimumSerializer(read_only=True)
    last_modified_by = UserBaseMinimumSerializer(read_only=True)

    class Meta:
        model = Policy
        exclude = ("deleted", "external_id")
        read_only_fields = TIMESTAMP_FIELDS

    def validate(self, attrs):
        if "patient" in attrs:
            patient = get_object_or_404(
                PatientRegistration.objects.filter(external_id=attrs["patient"]),
            )
            attrs["patient"] = patient
        else:
            raise ValidationError({"patient": "Field is Required"})
        return super().validate(attrs)

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        validated_data["last_modified_by"] = self.context["request"].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        instance.last_modified_by = self.context["request"].user
        return super().update(instance, validated_data)
