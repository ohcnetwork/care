from datetime import timedelta

from django.utils.timezone import localtime, now
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.api.serializers.bed import ConsultationBedSerializer
from care.facility.api.serializers.daily_round import DailyRoundSerializer
from care.facility.api.serializers.facility import FacilityBasicInfoSerializer
from care.facility.models import (
    CATEGORY_CHOICES,
    COVID_CATEGORY_CHOICES,
    Facility,
    PatientRegistration,
)
from care.facility.models.bed import Bed, ConsultationBed
from care.facility.models.notification import Notification
from care.facility.models.patient_base import (
    DISCHARGE_REASON_CHOICES,
    SYMPTOM_CHOICES,
    SuggestionChoices,
)
from care.facility.models.patient_consultation import PatientConsultation
from care.users.api.serializers.user import (
    UserAssignedSerializer,
    UserBaseMinimumSerializer,
)
from care.users.models import User
from care.utils.notification_handler import NotificationGenerator
from care.utils.queryset.facility import get_home_facility_queryset
from care.utils.serializer.external_id_field import ExternalIdSerializerField
from config.serializers import ChoiceField


class PatientConsultationSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="external_id", read_only=True)
    facility_name = serializers.CharField(source="facility.name", read_only=True)
    suggestion_text = ChoiceField(
        choices=PatientConsultation.SUGGESTION_CHOICES,
        read_only=True,
        source="suggestion",
    )

    symptoms = serializers.MultipleChoiceField(choices=SYMPTOM_CHOICES)
    deprecated_covid_category = ChoiceField(
        choices=COVID_CATEGORY_CHOICES, required=False
    )
    category = ChoiceField(choices=CATEGORY_CHOICES, required=True)

    referred_to_object = FacilityBasicInfoSerializer(
        source="referred_to", read_only=True
    )
    referred_to = ExternalIdSerializerField(
        queryset=Facility.objects.all(), required=False
    )
    patient = ExternalIdSerializerField(queryset=PatientRegistration.objects.all())
    facility = ExternalIdSerializerField(read_only=True)

    assigned_to_object = UserAssignedSerializer(source="assigned_to", read_only=True)

    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )

    discharge_reason = serializers.ChoiceField(
        choices=DISCHARGE_REASON_CHOICES, read_only=True, required=False
    )
    discharge_notes = serializers.CharField(read_only=True)

    action = ChoiceField(
        choices=PatientRegistration.ActionChoices, write_only=True, required=False
    )

    review_time = serializers.IntegerField(default=-1, write_only=True, required=False)

    last_edited_by = UserBaseMinimumSerializer(read_only=True)
    created_by = UserBaseMinimumSerializer(read_only=True)
    last_daily_round = DailyRoundSerializer(read_only=True)

    current_bed = ConsultationBedSerializer(read_only=True)

    bed = ExternalIdSerializerField(queryset=Bed.objects.all(), required=False)

    icd11_diagnoses_object = serializers.SerializerMethodField(read_only=True)

    icd11_provisional_diagnoses_object = serializers.SerializerMethodField(
        read_only=True
    )

    def get_icd11_diagnoses_objects_by_ids(self, diagnoses_ids):
        from care.facility.static_data.icd11 import ICDDiseases

        diagnosis_objects = []
        for diagnosis in diagnoses_ids:
            try:
                diagnosis_object = ICDDiseases.by.id[diagnosis].__dict__
                diagnosis_objects.append(diagnosis_object)
            except BaseException:
                pass
        return diagnosis_objects

    def get_icd11_diagnoses_object(self, consultation):
        return self.get_icd11_diagnoses_objects_by_ids(consultation.icd11_diagnoses)

    def get_icd11_provisional_diagnoses_object(self, consultation):
        return self.get_icd11_diagnoses_objects_by_ids(consultation.icd11_provisional_diagnoses)

    class Meta:
        model = PatientConsultation
        read_only_fields = TIMESTAMP_FIELDS + (
            "last_updated_by_telemedicine",
            "discharge_date",
            "last_edited_by",
            "created_by",
            "kasp_enabled_date",
        )
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
            raise ValidationError(
                {"consultation": ["Discharged Consultation data cannot be updated"]}
            )

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
                    patient.review_time = localtime(now()) + timedelta(
                        minutes=review_time
                    )
            patient.save()

        validated_data["last_updated_by_telemedicine"] = (
            self.context["request"].user == instance.assigned_to
        )

        if "is_kasp" in validated_data:
            if validated_data["is_kasp"] and (not instance.is_kasp):
                validated_data["kasp_enabled_date"] = localtime(now())

        _temp = instance.assigned_to

        consultation = super().update(instance, validated_data)

        if "assigned_to" in validated_data:
            if validated_data["assigned_to"] != _temp and validated_data["assigned_to"]:
                NotificationGenerator(
                    event=Notification.Event.PATIENT_CONSULTATION_ASSIGNMENT,
                    caused_by=self.context["request"].user,
                    caused_object=instance,
                    facility=instance.patient.facility,
                    notification_mediums=[
                        Notification.Medium.SYSTEM,
                        Notification.Medium.WHATSAPP,
                    ],
                ).generate()

        NotificationGenerator(
            event=Notification.Event.PATIENT_CONSULTATION_UPDATED,
            caused_by=self.context["request"].user,
            caused_object=consultation,
            facility=consultation.patient.facility,
        ).generate()

        return consultation

    def create(self, validated_data):

        action = -1
        review_time = -1
        if "action" in validated_data:
            action = validated_data.pop("action")
        if "review_time" in validated_data:
            review_time = validated_data.pop("review_time")

        # Authorisation Check

        allowed_facilities = get_home_facility_queryset(self.context["request"].user)
        if not allowed_facilities.filter(
            id=self.validated_data["patient"].facility.id
        ).exists():
            raise ValidationError(
                {"facility": "Consultation creates are only allowed in home facility"}
            )

        # End Authorisation Checks

        if validated_data["patient"].last_consultation:
            if (
                self.context["request"].user
                == validated_data["patient"].last_consultation.assigned_to
            ):
                raise ValidationError(
                    {
                        "Permission Denied": "Only Facility Staff can create consultation for a Patient"
                    },
                )

        if validated_data["patient"].last_consultation:
            if not validated_data["patient"].last_consultation.discharge_date:
                raise ValidationError(
                    {"consultation": "Exists please Edit Existing Consultation"}
                )

        if "is_kasp" in validated_data:
            if validated_data["is_kasp"]:
                validated_data["kasp_enabled_date"] = localtime(now())

        bed = validated_data.pop("bed", None)

        validated_data["facility_id"] = validated_data[
            "patient"
        ].facility_id  # Coercing facility as the patient's facility
        consultation = super().create(validated_data)
        consultation.created_by = self.context["request"].user
        consultation.last_edited_by = self.context["request"].user
        consultation.save()

        if bed:
            consultation_bed = ConsultationBed(
                bed=bed, consultation=consultation, start_date=consultation.created_date
            )
            consultation_bed.save()
            consultation.current_bed = consultation_bed
            consultation.save(update_fields=["current_bed"])

        patient = consultation.patient
        if consultation.suggestion == SuggestionChoices.OP:
            consultation.discharge_date = localtime(now())
            consultation.save()
            patient.is_active = False
            patient.allow_transfer = True
        else:
            patient.is_active = True
        patient.last_consultation = consultation

        if action != -1:
            patient.action = action
        if review_time > 0:
            patient.review_time = localtime(now()) + timedelta(minutes=review_time)

        patient.save()
        NotificationGenerator(
            event=Notification.Event.PATIENT_CONSULTATION_CREATED,
            caused_by=self.context["request"].user,
            caused_object=consultation,
            facility=patient.facility,
        ).generate()

        if consultation.assigned_to:
            NotificationGenerator(
                event=Notification.Event.PATIENT_CONSULTATION_ASSIGNMENT,
                caused_by=self.context["request"].user,
                caused_object=consultation,
                facility=consultation.patient.facility,
                notification_mediums=[
                    Notification.Medium.SYSTEM,
                    Notification.Medium.WHATSAPP,
                ],
            ).generate()

        return consultation

    def validate(self, attrs):
        validated = super().validate(attrs)
        # TODO Add Bed Authorisation Validation

        if "suggestion" in validated:
            if validated["suggestion"] is SuggestionChoices.R and not validated.get(
                "referred_to"
            ):
                raise ValidationError(
                    {
                        "referred_to": [
                            f"This field is required as the suggestion is {SuggestionChoices.R}."
                        ]
                    }
                )
            if (
                validated["suggestion"] is SuggestionChoices.A
                and validated.get("admitted")
                and not validated.get("admission_date")
            ):
                raise ValidationError(
                    {
                        "admission_date": [
                            "This field is required as the patient has been admitted."
                        ]
                    }
                )

        if "action" in validated:
            if validated["action"] == PatientRegistration.ActionEnum.REVIEW:
                if "review_time" not in validated:
                    raise ValidationError(
                        {
                            "review_time": [
                                "This field is required as the patient has been requested Review."
                            ]
                        }
                    )
                if validated["review_time"] <= 0:
                    raise ValidationError(
                        {"review_time": ["This field value is must be greater than 0."]}
                    )
        from care.facility.static_data.icd11 import ICDDiseases

        if "icd11_diagnoses" in validated:
            for diagnosis in validated["icd11_diagnoses"]:
                try:
                    ICDDiseases.by.id[diagnosis]
                except BaseException:
                    raise ValidationError(
                        {
                            "icd11_diagnoses": [
                                f"{diagnosis} is not a valid ICD 11 Diagnosis ID"
                            ]
                        }
                    )

        if "icd11_provisional_diagnoses" in validated:
            for diagnosis in validated["icd11_provisional_diagnoses"]:
                try:
                    ICDDiseases.by.id[diagnosis]
                except BaseException:
                    raise ValidationError(
                        {
                            "icd11_provisional_diagnoses": [
                                f"{diagnosis} is not a valid ICD 11 Diagnosis ID"
                            ]
                        }
                    )

        return validated


class PatientConsultationIDSerializer(serializers.ModelSerializer):
    consultation_id = serializers.UUIDField(source="external_id", read_only=True)
    patient_id = serializers.UUIDField(source="patient.external_id", read_only=True)

    class Meta:
        model = PatientConsultation
        fields = ("consultation_id", "patient_id")
