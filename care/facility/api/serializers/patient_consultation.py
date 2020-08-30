from datetime import timedelta

from django.utils.timezone import localtime, now
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.api.serializers.facility import FacilityBasicInfoSerializer
from care.facility.models import CATEGORY_CHOICES, Facility, PatientRegistration
from care.facility.models.patient_base import ADMIT_CHOICES, CURRENT_HEALTH_CHOICES, SYMPTOM_CHOICES, SuggestionChoices
from care.facility.models.patient_consultation import DailyRound, PatientConsultation
from care.users.api.serializers.user import UserBaseMinimumSerializer
from care.users.models import User
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

    assigned_to_object = UserBaseMinimumSerializer(source="assigned_to", read_only=True)

    assigned_to = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False, allow_null=True)

    action = ChoiceField(choices=PatientRegistration.ActionChoices, write_only=True, required=False)
    review_time = serializers.IntegerField(default=-1, write_only=True, required=False)

    last_edited_by = UserBaseMinimumSerializer(read_only=True)
    created_by = UserBaseMinimumSerializer(read_only=True)

    class Meta:
        model = PatientConsultation
        read_only = TIMESTAMP_FIELDS + ("discharge_date", "last_edited_by", "created_by")
        exclude = ("deleted", "external_id")

    def validate_bed_number(self, bed_number):
        try:
            if not self.initial_data["admitted"]:
                bed_number = None
        except KeyError:
            bed_number = None
        return bed_number

    def update(self, instance, validated_data):

        instance.last_edited_by = self.context["request"].user

        if instance.discharge_date:
            raise ValidationError({"consultation": [f"Discharged Consultation data cannot be updated"]})

        if instance.suggestion == SuggestionChoices.OP:
            instance.discharge_date = localtime(now())
            instance.save()

        if "action" in validated_data or "review_time" in validated_data:
            patient = instance.patient

            if "action" in validated_data:
                action = validated_data.pop("action")
                patient.action = action

            if "review_time" in validated_data:
                review_time = validated_data.pop("review_time")
                if review_time >= 0:
                    patient.review_time = localtime(now()) + timedelta(minutes=review_time)
            patient.save()

        return super().update(instance, validated_data)

    def create(self, validated_data):

        action = -1
        review_time = -1
        if "action" in validated_data:
            action = validated_data.pop("action")
        if "review_time" in validated_data:
            review_time = validated_data.pop("review_time")

        consultation = super().create(validated_data)
        consultation.created_by = self.context["request"].user
        consultation.last_edited_by = self.context["request"].user
        consultation.save()

        patient = consultation.patient
        if consultation.suggestion == SuggestionChoices.OP:
            consultation.discharge_date = localtime(now())
            consultation.save()
            patient.is_active = False
            patient.allow_transfer = True
        patient.last_consultation = consultation

        if action != -1:
            patient.action = action
        if review_time > 0:
            patient.review_time = localtime(now()) + timedelta(minutes=review_time)

        patient.save()

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

        if "action" in validated:
            if validated["action"] == PatientRegistration.ActionEnum.REVIEW:
                if "review_time" not in validated:
                    raise ValidationError(
                        {"review_time": [f"This field is required as the patient has been requested Review."]}
                    )
                if validated["review_time"] <= 0:
                    raise ValidationError({"review_time": [f"This field value is must be greater than 0."]})
        return validated


class DailyRoundSerializer(serializers.ModelSerializer):
    additional_symptoms = serializers.MultipleChoiceField(choices=SYMPTOM_CHOICES, required=False)
    patient_category = ChoiceField(choices=CATEGORY_CHOICES, required=False)
    current_health = ChoiceField(choices=CURRENT_HEALTH_CHOICES, required=False)

    class Meta:
        model = DailyRound
        exclude = TIMESTAMP_FIELDS
