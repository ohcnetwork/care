from rest_framework.serializers import CharField, ModelSerializer, UUIDField

from care.facility.api.serializers.patient import PatientDetailSerializer
from care.facility.models.patient import PatientRegistration
from care.hcx.models.policy import (
    OutcomeEnum,
    Policy,
    PriorityEnum,
    PurposeEnum,
    StatusEnum,
)
from care.users.api.serializers.user import UserBaseMinimumSerializer
from care.utils.serializer.external_id_field import ExternalIdSerializerField
from config.serializers import ChoiceField

TIMESTAMP_FIELDS = (
    "created_date",
    "modified_date",
)


class PolicySerializer(ModelSerializer):
    id = UUIDField(source="external_id", read_only=True)

    patient = ExternalIdSerializerField(
        queryset=PatientRegistration.objects.all(), write_only=True, required=True
    )
    patient_object = PatientDetailSerializer(source="patient", read_only=True)

    subscriber_id = CharField()
    policy_id = CharField()

    insurer_id = CharField(required=False)
    insurer_name = CharField(required=False)

    status = ChoiceField(choices=StatusEnum.choices, required=False)
    priority = ChoiceField(choices=PriorityEnum.choices, required=False)
    purpose = ChoiceField(choices=PurposeEnum.choices, required=False)

    outcome = ChoiceField(choices=OutcomeEnum.choices, read_only=True)
    error_text = CharField(read_only=True)

    created_by = UserBaseMinimumSerializer(read_only=True)
    last_modified_by = UserBaseMinimumSerializer(read_only=True)

    class Meta:
        model = Policy
        exclude = ("deleted", "external_id")
        read_only_fields = TIMESTAMP_FIELDS

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        validated_data["last_modified_by"] = self.context["request"].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        instance.last_modified_by = self.context["request"].user
        return super().update(instance, validated_data)
