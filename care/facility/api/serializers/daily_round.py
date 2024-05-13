from datetime import timedelta
from uuid import uuid4

from django.db import transaction
from django.utils import timezone
from django.utils.timezone import localtime, now
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from care.facility.events.handler import create_consultation_events

# from care.facility.api.serializers.bed import BedSerializer
from care.facility.models import (
    CATEGORY_CHOICES,
    COVID_CATEGORY_CHOICES,
    PatientRegistration,
)
from care.facility.models.bed import Bed
from care.facility.models.daily_round import DailyRound
from care.facility.models.notification import Notification
from care.facility.models.patient_base import (
    CURRENT_HEALTH_CHOICES,
    SYMPTOM_CHOICES,
    SuggestionChoices,
)
from care.facility.models.patient_consultation import PatientConsultation
from care.users.api.serializers.user import UserBaseMinimumSerializer
from care.utils.notification_handler import NotificationGenerator
from care.utils.queryset.facility import get_home_facility_queryset
from config.serializers import ChoiceField


class DailyRoundSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="external_id", read_only=True)
    additional_symptoms = serializers.MultipleChoiceField(
        choices=SYMPTOM_CHOICES, required=False
    )
    deprecated_covid_category = ChoiceField(
        choices=COVID_CATEGORY_CHOICES, required=False
    )  # Deprecated
    patient_category = ChoiceField(choices=CATEGORY_CHOICES, required=False)
    current_health = ChoiceField(choices=CURRENT_HEALTH_CHOICES, required=False)

    action = ChoiceField(
        choices=PatientRegistration.ActionChoices, write_only=True, required=False
    )
    review_interval = serializers.IntegerField(
        source="consultation__review_interval", required=False
    )

    taken_at = serializers.DateTimeField(required=True)

    rounds_type = ChoiceField(choices=DailyRound.RoundsTypeChoice, required=True)

    # Critical Care Components

    consciousness_level = ChoiceField(
        choices=DailyRound.ConsciousnessChoice, required=False
    )
    left_pupil_light_reaction = ChoiceField(
        choices=DailyRound.PupilReactionChoice, required=False
    )
    right_pupil_light_reaction = ChoiceField(
        choices=DailyRound.PupilReactionChoice, required=False
    )
    limb_response_upper_extremity_right = ChoiceField(
        choices=DailyRound.LimbResponseChoice, required=False
    )
    limb_response_upper_extremity_left = ChoiceField(
        choices=DailyRound.LimbResponseChoice, required=False
    )
    limb_response_lower_extremity_left = ChoiceField(
        choices=DailyRound.LimbResponseChoice, required=False
    )
    limb_response_lower_extremity_right = ChoiceField(
        choices=DailyRound.LimbResponseChoice, required=False
    )
    rhythm = ChoiceField(choices=DailyRound.RythmnChoice, required=False)
    ventilator_interface = ChoiceField(
        choices=DailyRound.VentilatorInterfaceChoice, required=False
    )
    ventilator_mode = ChoiceField(
        choices=DailyRound.VentilatorModeChoice, required=False
    )
    ventilator_oxygen_modality = ChoiceField(
        choices=DailyRound.VentilatorOxygenModalityChoice, required=False
    )
    insulin_intake_frequency = ChoiceField(
        choices=DailyRound.InsulinIntakeFrequencyChoice, required=False
    )

    clone_last = serializers.BooleanField(
        write_only=True, default=False, required=False
    )

    last_edited_by = UserBaseMinimumSerializer(read_only=True)
    created_by = UserBaseMinimumSerializer(read_only=True)

    # bed_object = BedSerializer(read_only=True)

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
            if "clone_last" in validated_data:
                should_clone = validated_data.pop("clone_last")
                if should_clone:
                    last_objects = DailyRound.objects.filter(
                        consultation=consultation
                    ).order_by("-created_date")
                    if not last_objects.exists():
                        raise ValidationError(
                            {"daily_round": "No Daily Round record available to copy"}
                        )

                    if "rounds_type" not in validated_data:
                        raise ValidationError(
                            {"daily_round": "Rounds type is required to clone"}
                        )

                    rounds_type = validated_data.get("rounds_type")
                    if rounds_type == DailyRound.RoundsType.NORMAL.value:
                        fields_to_clone = [
                            "consultation_id",
                            "patient_category",
                            "taken_at",
                            "additional_symptoms",
                            "other_symptoms",
                            "physical_examination_info",
                            "other_details",
                            "bp",
                            "pulse",
                            "resp",
                            "temperature",
                            "rhythm",
                            "rhythm_detail",
                            "ventilator_spo2",
                            "consciousness_level",
                        ]
                        cloned_daily_round_obj = DailyRound()
                        for field in fields_to_clone:
                            value = getattr(last_objects[0], field)
                            setattr(cloned_daily_round_obj, field, value)
                    else:
                        cloned_daily_round_obj = last_objects[0]

                    cloned_daily_round_obj.pk = None
                    cloned_daily_round_obj.rounds_type = rounds_type
                    cloned_daily_round_obj.created_by = self.context["request"].user
                    cloned_daily_round_obj.last_edited_by = self.context["request"].user
                    cloned_daily_round_obj.created_date = timezone.now()
                    cloned_daily_round_obj.modified_date = timezone.now()
                    cloned_daily_round_obj.external_id = uuid4()
                    cloned_daily_round_obj.save()
                    self.update_last_daily_round(cloned_daily_round_obj)
                    return self.update(cloned_daily_round_obj, validated_data)

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

            create_consultation_events(
                daily_round_obj.consultation_id,
                daily_round_obj,
                daily_round_obj.created_by_id,
                daily_round_obj.created_date,
            )
            return daily_round_obj

    def validate(self, attrs):
        validated = super().validate(attrs)
        validated["consultation"] = self.context["consultation"]

        if validated["consultation"].discharge_date:
            raise ValidationError(
                {"consultation": ["Discharged Consultation data cannot be updated"]}
            )

        if "action" in validated:
            if validated["action"] == PatientRegistration.ActionEnum.REVIEW:
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
                        {
                            "review_interval": [
                                "This field value is must be greater than 0."
                            ]
                        }
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
