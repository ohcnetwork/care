from datetime import timedelta
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone
from django.utils.timezone import localtime, now
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from care.facility.models import (
    CATEGORY_CHOICES,
    COVID_CATEGORY_CHOICES,
    PatientRegistration,
)
from care.facility.models.bed import Bed
from care.facility.models.daily_round import DailyRound
from care.facility.models.notification import Notification
from care.facility.models.patient_base import SuggestionChoices
from care.users.api.serializers.user import UserBaseMinimumSerializer
from care.utils.notification_handler import NotificationGenerator
from care.utils.queryset.facility import get_home_facility_queryset
from care.utils.serializers.fields import ChoiceField

if TYPE_CHECKING:
    from care.facility.models.patient_consultation import PatientConsultation


class DailyRoundSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="external_id", read_only=True)
    deprecated_covid_category = ChoiceField(
        choices=COVID_CATEGORY_CHOICES, required=False
    )  # Deprecated
    patient_category = ChoiceField(choices=CATEGORY_CHOICES, required=False)

    action = ChoiceField(
        choices=PatientRegistration.ActionChoices, write_only=True, required=False
    )
    review_interval = serializers.IntegerField(
        source="consultation__review_interval", required=False
    )

    taken_at = serializers.DateTimeField(required=True)

    rounds_type = ChoiceField(choices=DailyRound.RoundsType.choices, required=True)

    # Community Nurse's Log

    bowel_issue = ChoiceField(
        choices=DailyRound.BowelDifficultyType.choices, required=False
    )
    bladder_drainage = ChoiceField(
        choices=DailyRound.BladderDrainageType.choices, required=False
    )
    bladder_issue = ChoiceField(
        choices=DailyRound.BladderIssueType.choices, required=False
    )
    urination_frequency = ChoiceField(
        choices=DailyRound.UrinationFrequencyType.choices, required=False
    )
    sleep = ChoiceField(choices=DailyRound.SleepType.choices, required=False)
    nutrition_route = ChoiceField(
        choices=DailyRound.NutritionRouteType.choices, required=False
    )
    oral_issue = ChoiceField(choices=DailyRound.OralIssueType.choices, required=False)
    appetite = ChoiceField(choices=DailyRound.AppetiteType.choices, required=False)

    # Critical Care Components

    consciousness_level = ChoiceField(
        choices=DailyRound.ConsciousnessTypeChoice.choices, required=False
    )
    left_pupil_light_reaction = ChoiceField(
        choices=DailyRound.PupilReactionType.choices, required=False
    )
    right_pupil_light_reaction = ChoiceField(
        choices=DailyRound.PupilReactionType.choices, required=False
    )
    limb_response_upper_extremity_right = ChoiceField(
        choices=DailyRound.LimbResponseType.choices, required=False
    )
    limb_response_upper_extremity_left = ChoiceField(
        choices=DailyRound.LimbResponseType.choices, required=False
    )
    limb_response_lower_extremity_left = ChoiceField(
        choices=DailyRound.LimbResponseType.choices, required=False
    )
    limb_response_lower_extremity_right = ChoiceField(
        choices=DailyRound.LimbResponseType.choices, required=False
    )
    rhythm = ChoiceField(choices=DailyRound.RythmnType.choices, required=False)
    ventilator_interface = ChoiceField(
        choices=DailyRound.VentilatorInterfaceType.choices, required=False
    )
    ventilator_mode = ChoiceField(
        choices=DailyRound.VentilatorModeType.choices, required=False
    )
    ventilator_oxygen_modality = ChoiceField(
        choices=DailyRound.VentilatorOxygenModalityType.choices, required=False
    )
    insulin_intake_frequency = ChoiceField(
        choices=DailyRound.InsulinIntakeFrequencyType.choices, required=False
    )

    last_edited_by = UserBaseMinimumSerializer(read_only=True)
    created_by = UserBaseMinimumSerializer(read_only=True)

    class Meta:
        model = DailyRound
        read_only_fields = (
            "last_updated_by_telemedicine",
            "created_by_telemedicine",
            "glasgow_total_calculated",
            "total_intake_calculated",
            "total_output_calculated",
            "consultation",
        )
        exclude = ("deleted",)

    def validate_bp(self, value):
        if value is not None:
            sys, dia = value.get("systolic"), value.get("diastolic")
            if sys is not None and dia is not None and sys < dia:
                msg = "Systolic must be greater than diastolic"
                raise ValidationError(msg)
        return value

    def update(self, instance, validated_data):
        instance.last_edited_by = self.context["request"].user

        if instance.consultation.discharge_date:
            raise ValidationError(
                {"consultation": ["Discharged Consultation data cannot be updated"]}
            )

        if (
            "action" in validated_data
            or "consultation__review_interval" in validated_data
        ):
            patient = instance.consultation.patient

            if "action" in validated_data:
                action = validated_data.pop("action")
                patient.action = action

            if "consultation__review_interval" in validated_data:
                review_interval = validated_data.pop("consultation__review_interval")
                instance.consultation.review_interval = review_interval
                instance.consultation.save(update_fields=["review_interval"])
                if review_interval >= 0:
                    patient.review_time = localtime(now()) + timedelta(
                        minutes=review_interval
                    )
                else:
                    patient.review_time = None
            patient.save()

        validated_data["last_updated_by_telemedicine"] = False
        if self.context["request"].user == instance.consultation.assigned_to:
            validated_data["last_updated_by_telemedicine"] = True
        instance.consultation.save(update_fields=["last_updated_by_telemedicine"])

        NotificationGenerator(
            event=Notification.Event.PATIENT_CONSULTATION_UPDATE_UPDATED,
            caused_by=self.context["request"].user,
            caused_object=instance,
            facility=instance.consultation.patient.facility,
        ).generate()

        return super().update(instance, validated_data)

    def update_last_daily_round(self, daily_round_obj):
        consultation = daily_round_obj.consultation
        consultation.last_daily_round = daily_round_obj
        consultation.save()

        NotificationGenerator(
            event=Notification.Event.PATIENT_CONSULTATION_UPDATE_CREATED,
            caused_by=self.context["request"].user,
            caused_object=daily_round_obj,
            facility=daily_round_obj.consultation.patient.facility,
        ).generate()

    def create(self, validated_data):
        consultation: PatientConsultation = validated_data["consultation"]
        # Authorisation Checks
        if (
            not get_home_facility_queryset(self.context["request"].user)
            .filter(id=consultation.facility_id)
            .exists()
        ):
            raise ValidationError(
                {"facility": "Daily Round creates are only allowed in home facility"}
            )
        # Authorisation Checks End

        # Patient needs to have a bed assigned for admission
        if (
            not consultation.current_bed
            and consultation.suggestion == SuggestionChoices.A
        ):
            raise ValidationError(
                {
                    "bed": "Patient does not have a bed assigned. Please assign a bed first"
                }
            )

        with transaction.atomic():
            if (
                validated_data.get("rounds_type")
                == DailyRound.RoundsType.TELEMEDICINE.value
                and consultation.suggestion != SuggestionChoices.DC
            ):
                raise ValidationError(
                    {
                        "rounds_type": "Telemedicine Rounds are only allowed for Domiciliary Care patients"
                    }
                )

            if (
                "action" in validated_data
                or "consultation__review_interval" in validated_data
            ):
                patient = validated_data["consultation"].patient

                if "action" in validated_data:
                    action = validated_data.pop("action")
                    patient.action = action

                if "consultation__review_interval" in validated_data:
                    review_interval = validated_data.pop(
                        "consultation__review_interval"
                    )
                    validated_data["consultation"].review_interval = review_interval
                    if review_interval >= 0:
                        patient.review_time = localtime(now()) + timedelta(
                            minutes=review_interval
                        )
                    else:
                        patient.review_time = None
                patient.save()

            validated_data["created_by_telemedicine"] = False
            validated_data["last_updated_by_telemedicine"] = False

            if (
                self.context["request"].user
                == validated_data["consultation"].assigned_to
            ):
                validated_data["created_by_telemedicine"] = True
                validated_data["last_updated_by_telemedicine"] = True

            daily_round_obj: DailyRound = super().create(validated_data)
            daily_round_obj.created_by = self.context["request"].user
            daily_round_obj.last_edited_by = self.context["request"].user
            daily_round_obj.consultation.last_updated_by_telemedicine = validated_data[
                "last_updated_by_telemedicine"
            ]
            daily_round_obj.consultation.save(
                update_fields=["last_updated_by_telemedicine", "review_interval"]
            )
            daily_round_obj.save(
                update_fields=[
                    "created_by",
                    "last_edited_by",
                ]
            )

            if daily_round_obj.rounds_type != DailyRound.RoundsType.AUTOMATED.value:
                self.update_last_daily_round(daily_round_obj)

            return daily_round_obj

    def validate(self, attrs):
        validated = super().validate(attrs)
        validated["consultation"] = self.context["consultation"]

        if validated["consultation"].discharge_date:
            raise ValidationError(
                {"consultation": ["Discharged Consultation data cannot be updated"]}
            )

        if (
            "action" in validated
            and validated["action"] == PatientRegistration.ActionEnum.REVIEW
        ):
            if "consultation__review_interval" not in validated:
                raise ValidationError(
                    {
                        "review_interval": [
                            "This field is required as the patient has been requested Review."
                        ]
                    }
                )
            if validated["consultation__review_interval"] <= 0:
                raise ValidationError(
                    {"review_interval": ["This field value is must be greater than 0."]}
                )

        if "bed" in validated:
            external_id = validated.pop("bed")["external_id"]
            if external_id:
                # TODO add authorisation checks
                bed_object = Bed.objects.filter(external_id=external_id).first()
                if not bed_object:
                    raise ValidationError({"bed": ["Object not found."]})
                validated["bed_id"] = bed_object.id

        return validated

    def validate_taken_at(self, value):
        if value and value > timezone.now() + timedelta(minutes=2):
            msg = "Cannot create an update in the future"
            raise serializers.ValidationError(msg)
        return value
