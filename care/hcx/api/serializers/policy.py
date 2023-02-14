from rest_framework.serializers import ModelSerializer, UUIDField, CharField
from config.serializers import ChoiceField
from care.hcx.models.policy import Policy
from care.hcx.models.policy import STATUS_CHOICES, PRIORITY_CHOICES, PURPOSE_CHOICES, OUTCOME_CHOICES
from django.shortcuts import get_object_or_404
from care.facility.models.patient import PatientRegistration
from care.facility.api.serializers.patient import PatientDetailSerializer
from rest_framework.exceptions import ValidationError

TIMESTAMP_FIELDS = (
    "created_date",
    "modified_date",
)

class PolicySerializer(ModelSerializer):
    id = UUIDField(source="external_id", read_only=True)

    patient = UUIDField(write_only=True, required=True)
    patient_object = PatientDetailSerializer(source="patient", read_only=True)

    subscriber_id =  CharField()
    policy_id = CharField()
    
    insurer_id = CharField()
    insurer_name = CharField()

    status = ChoiceField(choices=STATUS_CHOICES)
    priority = ChoiceField(choices=PRIORITY_CHOICES, default="normal")
    purpose = ChoiceField(choices=PURPOSE_CHOICES)
    
    outcome = ChoiceField(choices=OUTCOME_CHOICES, read_only=True)
    error_text = CharField()


    class Meta:
        model = Policy
        exclude = ("deleted", "external_id")
        read_only_fields = TIMESTAMP_FIELDS

    def validate(self, attrs):
        if "patient" in attrs:
            patient = get_object_or_404(
                PatientRegistration.objects.filter(external_id=attrs["patient"])
            )
            attrs["patient"] = patient
        else:
            raise ValidationError(
                {"patient": "Field is Required"}
            )
        return super().validate(attrs)