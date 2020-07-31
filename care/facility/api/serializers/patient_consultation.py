from django.utils.timezone import localtime, now
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.api.serializers.facility import FacilityBasicInfoSerializer
from care.facility.models import CATEGORY_CHOICES, Facility, PatientRegistration
from care.facility.models.patient_base import ADMIT_CHOICES, CURRENT_HEALTH_CHOICES, SYMPTOM_CHOICES, SuggestionChoices
from care.facility.models.patient_consultation import DailyRound, PatientConsultation
from care.utils.serializer.external_id_field import ExternalIdSerializerField
from config.serializers import ChoiceField


class PatientConsultationSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="external_id", read_only=True)
    facility_name = serializers.CharField(source="facility.name", read_only=True)
    suggestion_text = ChoiceField(choices=PatientConsultation.SUGGESTION_CHOICES, read_only=True, source="suggestion")

    symptoms = serializers.MultipleChoiceField(choices=SYMPTOM_CHOICES)
    category = ChoiceField(choices=CATEGORY_CHOICES, required=False)
    admitted_to = ChoiceField(choices=ADMIT_CHOICES, required=False)

    referred_to_object = FacilityBasicInfoSerializer(source="referred_to", read_only=True)
    referred_to = ExternalIdSerializerField(queryset=Facility.objects.all(), required=False)
    patient = ExternalIdSerializerField(queryset=PatientRegistration.objects.all())
    facility = ExternalIdSerializerField(queryset=Facility.objects.all())

    class Meta:
        model = PatientConsultation
        read_only = TIMESTAMP_FIELDS + ("discharge_date",)
        exclude = (
            "deleted",
            "external_id",
        )

    def validate_bed_number(self, bed_number):
        try:
            if not self.initial_data["admitted"]:
                bed_number = None
        except KeyError:
            bed_number = None
        return bed_number

    def update(self, instance, validated_data):
        if instance.discharge_date:
            return ValidationError({"consultation": [f"Discharged Consultation data cannot be updated"]})

        if instance.suggestion == SuggestionChoices.OP:
            instance.discharge_date = localtime(now())
            instance.save()

        return super().update(instance, validated_data)

    def create(self, validated_data):

        consultation = super().create(validated_data)

        if consultation.suggestion == SuggestionChoices.OP:
            consultation.discharge_date = localtime(now())
            consultation.save()

        return consultation

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
        exclude = TIMESTAMP_FIELDS
