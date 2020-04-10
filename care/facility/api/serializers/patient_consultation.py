from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.models import CATEGORY_CHOICES
from care.facility.models.patient_base import ADMIT_CHOICES, CURRENT_HEALTH_CHOICES, SYMPTOM_CHOICES, SuggestionChoices
from care.facility.models.patient_consultation import DailyRound, PatientConsultation
from config.serializers import ChoiceField


class PatientConsultationSerializer(serializers.ModelSerializer):
    facility_name = serializers.CharField(source="facility.name", read_only=True)
    suggestion_text = ChoiceField(choices=PatientConsultation.SUGGESTION_CHOICES, read_only=True, source="suggestion")

    symptoms = serializers.MultipleChoiceField(choices=SYMPTOM_CHOICES)
    category = ChoiceField(choices=CATEGORY_CHOICES, required=False)
    admitted_to = ChoiceField(choices=ADMIT_CHOICES, required=False)

    class Meta:
        model = PatientConsultation
        read_only = TIMESTAMP_FIELDS
        exclude = ("deleted",)

    def validate(self, obj):
        validated = super().validate(obj)
        if validated["suggestion"] is SuggestionChoices.R and not validated.get("referred_to"):
            raise ValidationError(
                {"referred_to": [f"This field is required as the suggestion is {SuggestionChoices.R}."]}
            )
        if (
            validated["suggestion"] is SuggestionChoices.A
            and validated.get("admitted")
            and not validated.get("admission_date")
        ):
            raise ValidationError({"admission_date": [f"This field is required as the patient has been admitted."]})
        return validated


class DailyRoundSerializer(serializers.ModelSerializer):
    additional_symptoms = serializers.MultipleChoiceField(choices=SYMPTOM_CHOICES, required=False)
    patient_category = ChoiceField(choices=CATEGORY_CHOICES, required=False)
    current_health = ChoiceField(choices=CURRENT_HEALTH_CHOICES, required=False)

    class Meta:
        model = DailyRound
        fields = "__all__"
