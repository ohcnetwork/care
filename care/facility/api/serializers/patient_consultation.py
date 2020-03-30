from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from care.facility.models import DailyRound, PatientConsultation, SuggestionChoices


class PatientConsultationSerializer(serializers.ModelSerializer):
    facility_name = serializers.CharField(source="facility.name", read_only=True)

    class Meta:
        model = PatientConsultation
        fields = "__all__"

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
    class Meta:
        model = DailyRound
        fields = "__all__"
