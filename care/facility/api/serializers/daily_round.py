from datetime import timedelta
from uuid import uuid4

from django.utils import timezone
from django.utils.timezone import localtime, now
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404

# from care.facility.api.serializers.bed import BedSerializer
from care.facility.models import CATEGORY_CHOICES, PatientRegistration
from care.facility.models.bed import Bed
from care.facility.models.daily_round import DailyRound
from care.facility.models.notification import Notification
from care.facility.models.patient_base import ADMIT_CHOICES, CURRENT_HEALTH_CHOICES, SYMPTOM_CHOICES
from care.users.api.serializers.user import UserBaseMinimumSerializer
from care.utils.notification_handler import NotificationGenerator
from care.utils.queryset.consultation import get_consultation_queryset
from config.serializers import ChoiceField


class DailyRoundSerializer(serializers.ModelSerializer):

    id = serializers.CharField(source="external_id", read_only=True)
    additional_symptoms = serializers.MultipleChoiceField(choices=SYMPTOM_CHOICES, required=False)
    patient_category = ChoiceField(choices=CATEGORY_CHOICES, required=False)
    current_health = ChoiceField(choices=CURRENT_HEALTH_CHOICES, required=False)

    action = ChoiceField(choices=PatientRegistration.ActionChoices, write_only=True, required=False)
    review_time = serializers.IntegerField(default=-1, write_only=True, required=False)

    taken_at = serializers.DateTimeField(required=True)

    rounds_type = ChoiceField(choices=DailyRound.RoundsTypeChoice, required=True)

    # Critical Care Components

    consciousness_level = ChoiceField(choices=DailyRound.ConsciousnessChoice, required=False)
    left_pupil_light_reaction = ChoiceField(choices=DailyRound.PupilReactionChoice, required=False)
    right_pupil_light_reaction = ChoiceField(choices=DailyRound.PupilReactionChoice, required=False)
    limb_response_upper_extremity_right = ChoiceField(choices=DailyRound.LimbResponseChoice, required=False)
    limb_response_upper_extremity_left = ChoiceField(choices=DailyRound.LimbResponseChoice, required=False)
    limb_response_lower_extremity_left = ChoiceField(choices=DailyRound.LimbResponseChoice, required=False)
    limb_response_lower_extremity_right = ChoiceField(choices=DailyRound.LimbResponseChoice, required=False)
    rhythm = ChoiceField(choices=DailyRound.RythmnChoice, required=False)
    ventilator_interface = ChoiceField(choices=DailyRound.VentilatorInterfaceChoice, required=False)
    ventilator_mode = ChoiceField(choices=DailyRound.VentilatorModeChoice, required=False)
    ventilator_oxygen_modality = ChoiceField(choices=DailyRound.VentilatorOxygenModalityChoice, required=False)
    insulin_intake_frequency = ChoiceField(choices=DailyRound.InsulinIntakeFrequencyChoice, required=False)

    clone_last = serializers.BooleanField(write_only=True, default=False, required=False)

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
        )
        exclude = ("deleted",)

    def update(self, instance, validated_data):

        instance.last_edited_by = self.context["request"].user

        if instance.consultation.discharge_date:
            raise ValidationError({"consultation": [f"Discharged Consultation data cannot be updated"]})

        if "action" in validated_data or "review_time" in validated_data:
            patient = instance.consultation.patient

            if "action" in validated_data:
                action = validated_data.pop("action")
                patient.action = action

            if "review_time" in validated_data:
                review_time = validated_data.pop("review_time")
                if review_time >= 0:
                    patient.review_time = localtime(now()) + timedelta(minutes=review_time)
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

        if "clone_last" in validated_data:
            should_clone = validated_data.pop("clone_last")
            if should_clone:
                consultation = get_object_or_404(
                    get_consultation_queryset(self.context["request"].user).filter(id=validated_data["consultation"].id)
                )
                last_objects = DailyRound.objects.filter(consultation=consultation).order_by("-created_date")
                if not last_objects.exists():
                    raise ValidationError({"daily_round": "No Daily Round record available to copy"})
                cloned_daily_round_obj = last_objects[0]
                cloned_daily_round_obj.pk = None
                cloned_daily_round_obj.created_by = self.context["request"].user
                cloned_daily_round_obj.last_edited_by = self.context["request"].user
                cloned_daily_round_obj.created_date = timezone.now()
                cloned_daily_round_obj.modified_date = timezone.now()
                cloned_daily_round_obj.external_id = uuid4()
                cloned_daily_round_obj.save()
                self.update_last_daily_round(cloned_daily_round_obj)
                return self.update(cloned_daily_round_obj, validated_data)

        if "action" in validated_data or "review_time" in validated_data:
            patient = validated_data["consultation"].patient

            if "action" in validated_data:
                action = validated_data.pop("action")
                patient.action = action

            if "review_time" in validated_data:
                review_time = validated_data.pop("review_time")
                if review_time >= 0:
                    patient.review_time = localtime(now()) + timedelta(minutes=review_time)
            patient.save()

        validated_data["created_by_telemedicine"] = False
        validated_data["last_updated_by_telemedicine"] = False

        if self.context["request"].user == validated_data["consultation"].assigned_to:
            validated_data["created_by_telemedicine"] = True
            validated_data["last_updated_by_telemedicine"] = True

        daily_round_obj = super().create(validated_data)
        daily_round_obj.created_by = self.context["request"].user
        daily_round_obj.last_edited_by = self.context["request"].user
        daily_round_obj.consultation.last_updated_by_telemedicine = validated_data["last_updated_by_telemedicine"]
        daily_round_obj.consultation.save(
            update_fields=[
                "last_updated_by_telemedicine",
                "created_by",
                "last_edited_by",
            ]
        )

        self.update_last_daily_round(daily_round_obj)
        return daily_round_obj

    def validate(self, obj):
        validated = super().validate(obj)

        if validated["consultation"].discharge_date:
            raise ValidationError({"consultation": [f"Discharged Consultation data cannot be updated"]})

        if "action" in validated:
            if validated["action"] == PatientRegistration.ActionEnum.REVIEW:
                if "review_time" not in validated:
                    raise ValidationError(
                        {"review_time": [f"This field is required as the patient has been requested Review."]}
                    )
                if validated["review_time"] <= 0:
                    raise ValidationError({"review_time": [f"This field value is must be greater than 0."]})

        if "bed" in validated:
            external_id = validated.pop("bed")["external_id"]
            if external_id:
                # TODO add authorisation checks
                bed_object = Bed.objects.filter(external_id=external_id).first()
                if not bed_object:
                    raise ValidationError({"bed": [f"Obeject not found."]})
                validated["bed_id"] = bed_object.id

        return validated
