from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.timezone import localtime, make_aware, now
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.api.serializers.asset import AssetLocationSerializer
from care.facility.api.serializers.bed import (
    AssetBedSerializer,
    ConsultationBedSerializer,
)
from care.facility.api.serializers.consultation_diagnosis import (
    ConsultationCreateDiagnosisSerializer,
    ConsultationDiagnosisSerializer,
)
from care.facility.api.serializers.daily_round import DailyRoundSerializer
from care.facility.api.serializers.encounter_symptom import (
    EncounterCreateSymptomSerializer,
    EncounterSymptomSerializer,
)
from care.facility.api.serializers.facility import FacilityBasicInfoSerializer
from care.facility.models import (
    CATEGORY_CHOICES,
    COVID_CATEGORY_CHOICES,
    Facility,
    PatientRegistration,
    Prescription,
    PrescriptionDosageType,
    PrescriptionType,
)
from care.facility.models.asset import AssetLocation
from care.facility.models.bed import Bed, ConsultationBed
from care.facility.models.encounter_symptom import (
    ClinicalImpressionStatus,
    EncounterSymptom,
    Symptom,
)
from care.facility.models.file_upload import FileUpload
from care.facility.models.icd11_diagnosis import (
    ConditionVerificationStatus,
    ConsultationDiagnosis,
)
from care.facility.models.notification import Notification
from care.facility.models.patient_base import (
    NewDischargeReasonEnum,
    RouteToFacility,
    SuggestionChoices,
)
from care.facility.models.patient_consultation import (
    ConsentType,
    PatientCodeStatusType,
    PatientConsent,
    PatientConsultation,
)
from care.users.api.serializers.user import (
    UserAssignedSerializer,
    UserBaseMinimumSerializer,
)
from care.users.models import User
from care.utils.lock import Lock
from care.utils.notification_handler import NotificationGenerator
from care.utils.queryset.facility import get_home_facility_queryset
from care.utils.serializers.fields import ChoiceField, ExternalIdSerializerField

MIN_ENCOUNTER_DATE = make_aware(settings.MIN_ENCOUNTER_DATE)


class PatientConsultationSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="external_id", read_only=True)
    facility_name = serializers.CharField(source="facility.name", read_only=True)
    suggestion_text = ChoiceField(
        choices=PatientConsultation.SUGGESTION_CHOICES,
        read_only=True,
        source="suggestion",
    )

    deprecated_covid_category = ChoiceField(
        choices=COVID_CATEGORY_CHOICES, required=False
    )
    category = ChoiceField(choices=CATEGORY_CHOICES, required=True)

    referred_to_object = FacilityBasicInfoSerializer(
        source="referred_to", read_only=True
    )
    referred_to = ExternalIdSerializerField(
        queryset=Facility.objects.all(),
        required=False,
    )
    referred_to_external = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )

    referred_from_facility_object = FacilityBasicInfoSerializer(
        source="referred_from_facility", read_only=True
    )
    referred_from_facility = ExternalIdSerializerField(
        queryset=Facility.objects.all(),
        required=False,
    )
    referred_from_facility_external = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    referred_by_external = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )

    transferred_from_location_object = AssetLocationSerializer(
        source="transferred_from_location", read_only=True
    )
    transferred_from_location = ExternalIdSerializerField(
        queryset=AssetLocation.objects.all(),
        required=False,
    )

    patient = ExternalIdSerializerField(queryset=PatientRegistration.objects.all())
    facility = ExternalIdSerializerField(read_only=True)

    assigned_to_object = UserAssignedSerializer(source="assigned_to", read_only=True)
    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )

    treating_physician_object = UserBaseMinimumSerializer(
        source="treating_physician", read_only=True
    )
    treating_physician = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )

    new_discharge_reason = serializers.ChoiceField(
        choices=NewDischargeReasonEnum.choices, read_only=True, required=False
    )
    discharge_notes = serializers.CharField(read_only=True)

    discharge_prescription = serializers.SerializerMethodField()
    discharge_prn_prescription = serializers.SerializerMethodField()

    action = ChoiceField(
        choices=PatientRegistration.ActionChoices,
        write_only=True,
        required=False,
    )

    review_interval = serializers.IntegerField(default=-1, required=False)

    last_edited_by = UserBaseMinimumSerializer(read_only=True)
    created_by = UserBaseMinimumSerializer(read_only=True)
    last_daily_round = DailyRoundSerializer(read_only=True)

    current_bed = ConsultationBedSerializer(read_only=True)

    bed = ExternalIdSerializerField(queryset=Bed.objects.all(), required=False)

    create_diagnoses = ConsultationCreateDiagnosisSerializer(
        many=True,
        write_only=True,
        required=False,
        help_text="Bulk create diagnoses for the consultation upon creation",
    )
    diagnoses = ConsultationDiagnosisSerializer(many=True, read_only=True)
    create_symptoms = EncounterCreateSymptomSerializer(
        many=True,
        write_only=True,
        required=False,
        help_text="Bulk create symptoms for the consultation upon creation",
    )
    symptoms = EncounterSymptomSerializer(many=True, read_only=True)
    medico_legal_case = serializers.BooleanField(default=False, required=False)

    def get_discharge_prescription(self, consultation):
        return (
            Prescription.objects.filter(
                consultation=consultation,
                prescription_type=PrescriptionType.DISCHARGE.value,
            )
            .exclude(dosage_type=PrescriptionDosageType.PRN.value)
            .values()
        )

    def get_discharge_prn_prescription(self, consultation):
        return Prescription.objects.filter(
            consultation=consultation,
            prescription_type=PrescriptionType.DISCHARGE.value,
            dosage_type=PrescriptionDosageType.PRN.value,
        ).values()

    def _lock_key(self, patient_id):
        return f"patient_consultation__patient_registration__{patient_id}"

    class Meta:
        model = PatientConsultation
        read_only_fields = (
            *TIMESTAMP_FIELDS,
            "last_updated_by_telemedicine",
            "discharge_date",
            "last_edited_by",
            "created_by",
            "kasp_enabled_date",
            "is_readmission",
            "deprecated_verified_by",
        )
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
        instance.last_edited_by = self.context["request"].user

        if instance.discharge_date:
            if "medico_legal_case" not in validated_data:
                raise ValidationError(
                    {"consultation": ["Discharged Consultation data cannot be updated"]}
                )
            instance.medico_legal_case = validated_data.pop("medico_legal_case")
            instance.save()
            return instance

        if instance.suggestion == SuggestionChoices.OP:
            instance.discharge_date = localtime(now())
            instance.save()

        if "action" in validated_data or "review_interval" in validated_data:
            patient = instance.patient

            if "action" in validated_data:
                action = validated_data.pop("action")
                patient.action = action

            if "review_interval" in validated_data:
                review_interval = validated_data.pop("review_interval")
                instance.review_interval = review_interval
                instance.save()
                if review_interval >= 0:
                    patient.review_time = localtime(now()) + timedelta(
                        minutes=review_interval
                    )
                else:
                    patient.review_time = None
            patient.save()

        validated_data["last_updated_by_telemedicine"] = (
            self.context["request"].user == instance.assigned_to
        )

        if (
            "is_kasp" in validated_data
            and validated_data["is_kasp"]
            and (not instance.is_kasp)
        ):
            validated_data["kasp_enabled_date"] = localtime(now())

        _temp = instance.assigned_to

        consultation = super().update(instance, validated_data)

        if (
            "assigned_to" in validated_data
            and validated_data["assigned_to"] != _temp
            and validated_data["assigned_to"]
        ):
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

    def create(self, validated_data):  # noqa: PLR0915 PLR0912
        if route_to_facility := validated_data.get("route_to_facility"):
            if route_to_facility == RouteToFacility.OUTPATIENT:
                validated_data["icu_admission_date"] = None
                validated_data["transferred_from_location"] = None
                validated_data["referred_from_facility"] = None
                validated_data["referred_from_facility_external"] = ""
                validated_data["referred_by_external"] = ""

            if route_to_facility == RouteToFacility.INTRA_FACILITY_TRANSFER:
                validated_data["referred_from_facility"] = None
                validated_data["referred_from_facility_external"] = ""
                validated_data["referred_by_external"] = ""

                if not validated_data.get("transferred_from_location"):
                    raise ValidationError(
                        {
                            "transferred_from_location": [
                                "This field is required as the patient has been transferred from another location."
                            ]
                        }
                    )

            if route_to_facility == RouteToFacility.INTER_FACILITY_TRANSFER:
                validated_data["transferred_from_location"] = None

                if not validated_data.get(
                    "referred_from_facility"
                ) and not validated_data.get("referred_from_facility_external"):
                    raise ValidationError(
                        {
                            "referred_from_facility": [
                                "This field is required as the patient has been referred from another facility."
                            ]
                        }
                    )

                if validated_data.get("referred_from_facility") and validated_data.get(
                    "referred_from_facility_external"
                ):
                    raise ValidationError(
                        {
                            "referred_from_facility": [
                                "Only one of referred_from_facility and referred_from_facility_external can be set"
                            ],
                            "referred_from_facility_external": [
                                "Only one of referred_from_facility and referred_from_facility_external can be set"
                            ],
                        }
                    )
        else:
            raise ValidationError({"route_to_facility": "This field is required"})

        create_diagnosis = validated_data.pop("create_diagnoses")
        create_symptoms = validated_data.pop("create_symptoms")

        action = validated_data.pop("action", -1)
        review_interval = validated_data.get("review_interval", -1)

        # Authorisation Check

        user = self.context["request"].user
        allowed_facilities = get_home_facility_queryset(user)
        if not allowed_facilities.filter(
            id=self.validated_data["patient"].facility_id
        ).exists():
            raise ValidationError(
                {"facility": "Consultation creates are only allowed in home facility"}
            )

        # End Authorisation Checks

        with (
            Lock(self._lock_key(validated_data["patient"].id)),
            transaction.atomic(),
        ):
            patient = validated_data["patient"]
            if patient.last_consultation:
                if patient.last_consultation.assigned_to == user:
                    raise ValidationError(
                        {
                            "Permission Denied": "Only Facility Staff can create consultation for a Patient"
                        },
                    )

                if not patient.last_consultation.discharge_date:
                    raise ValidationError(
                        {"consultation": "Exists please Edit Existing Consultation"}
                    )

            if validated_data.get("is_kasp"):
                validated_data["kasp_enabled_date"] = now()

            bed = validated_data.pop("bed", None)

            # Coercing facility as the patient's facility
            validated_data["facility_id"] = patient.facility_id

            consultation: PatientConsultation = super().create(validated_data)
            consultation.created_by = user
            consultation.last_edited_by = user
            consultation.previous_consultation = patient.last_consultation
            last_consultation = patient.last_consultation
            if (
                last_consultation
                and consultation.suggestion == SuggestionChoices.A
                and last_consultation.suggestion == SuggestionChoices.A
                and last_consultation.discharge_date
                and last_consultation.discharge_date + timedelta(days=30)
                > consultation.encounter_date
            ):
                consultation.is_readmission = True

            ConsultationDiagnosis.objects.bulk_create(
                [
                    ConsultationDiagnosis(
                        consultation=consultation,
                        diagnosis_id=obj["diagnosis"].id,
                        is_principal=obj["is_principal"],
                        verification_status=obj["verification_status"],
                        created_by=user,
                    )
                    for obj in create_diagnosis
                ]
            )

            EncounterSymptom.objects.bulk_create(
                EncounterSymptom(
                    consultation=consultation,
                    symptom=obj.get("symptom"),
                    onset_date=obj.get("onset_date"),
                    cure_date=obj.get("cure_date"),
                    clinical_impression_status=obj.get("clinical_impression_status"),
                    other_symptom=obj.get("other_symptom") or "",
                    created_by=user,
                )
                for obj in create_symptoms
            )

            if bed and consultation.suggestion == SuggestionChoices.A:
                consultation_bed = ConsultationBed(
                    bed=bed,
                    consultation=consultation,
                    start_date=consultation.created_date,
                )
                consultation_bed.save()
                consultation.current_bed = consultation_bed

            if consultation.suggestion == SuggestionChoices.OP:
                consultation.discharge_date = now()
                patient.is_active = False
                patient.allow_transfer = True
            else:
                patient.is_active = True
            patient.last_consultation = consultation

            if action != -1:
                patient.action = action

            if review_interval > 0:
                patient.review_time = now() + timedelta(minutes=review_interval)
            else:
                patient.review_time = None

            consultation.save()
            patient.save()

            NotificationGenerator(
                event=Notification.Event.PATIENT_CONSULTATION_CREATED,
                caused_by=user,
                caused_object=consultation,
                facility=patient.facility,
            ).generate()

            if consultation.assigned_to:
                NotificationGenerator(
                    event=Notification.Event.PATIENT_CONSULTATION_ASSIGNMENT,
                    caused_by=user,
                    caused_object=consultation,
                    facility=consultation.patient.facility,
                    notification_mediums=[
                        Notification.Medium.SYSTEM,
                        Notification.Medium.WHATSAPP,
                    ],
                ).generate()

            return consultation

    def validate_create_diagnoses(self, value):
        # Reject if create_diagnoses is present for edits
        if self.instance and value:
            msg = "Bulk create diagnoses is not allowed on update"
            raise ValidationError(msg)

        # Reject if no diagnoses are provided
        if len(value) == 0:
            msg = "Atleast one diagnosis is required"
            raise ValidationError(msg)

        # Reject if duplicate diagnoses are provided
        if len(value) != len({obj["diagnosis"].id for obj in value}):
            msg = "Duplicate diagnoses are not allowed"
            raise ValidationError(msg)

        principal_diagnosis, confirmed_diagnoses = None, []
        for obj in value:
            if obj["verification_status"] == ConditionVerificationStatus.CONFIRMED:
                confirmed_diagnoses.append(obj)

            # Reject if there are more than one principal diagnosis
            if obj["is_principal"]:
                if principal_diagnosis:
                    msg = "Only one diagnosis can be set as principal diagnosis"
                    raise ValidationError(msg)
                principal_diagnosis = obj

        # Reject if principal diagnosis is not one of confirmed diagnosis (if it is present)
        if (
            principal_diagnosis
            and len(confirmed_diagnoses)
            and principal_diagnosis["verification_status"]
            != ConditionVerificationStatus.CONFIRMED
        ):
            msg = "Only confirmed diagnosis can be set as principal diagnosis if it is present"
            raise ValidationError(msg)

        return value

    def validate_create_symptoms(self, value):
        if self.instance:
            msg = "Bulk create symptoms is not allowed on update"
            raise ValidationError(msg)

        counter: set[int | str] = set()
        for obj in value:
            item: int | str = obj["symptom"]
            if obj["symptom"] == Symptom.OTHERS:
                other_symptom = obj.get("other_symptom")
                if not other_symptom:
                    raise ValidationError(
                        {
                            "other_symptom": "Other symptom should not be empty when symptom type is OTHERS"
                        }
                    )
                item: str = other_symptom.strip().lower()
            if item in counter:
                # Reject if duplicate symptoms are provided
                msg = "Duplicate symptoms are not allowed"
                raise ValidationError(msg)
            if not obj.get("cure_date"):
                # skip duplicate symptom check for ones that has cure date
                counter.add(item)

        current_time = now()
        for obj in value:
            if obj["onset_date"] > current_time:
                raise ValidationError(
                    {"onset_date": "Onset date cannot be in the future"}
                )

            if cure_date := obj.get("cure_date"):
                if cure_date < obj["onset_date"]:
                    raise ValidationError(
                        {"cure_date": "Cure date should be after onset date"}
                    )
                obj["clinical_impression_status"] = ClinicalImpressionStatus.COMPLETED
            else:
                obj["clinical_impression_status"] = ClinicalImpressionStatus.IN_PROGRESS

        return value

    def validate_encounter_date(self, value):
        if value < MIN_ENCOUNTER_DATE:
            raise ValidationError(
                {
                    "encounter_date": [
                        f"This field value must be greater than {MIN_ENCOUNTER_DATE.strftime('%Y-%m-%d')}"
                    ]
                }
            )
        if value > now():
            raise ValidationError(
                {"encounter_date": "This field value cannot be in the future."}
            )
        return value

    def validate_patient_no(self, value):
        if value is None:
            return None
        return value.strip()

    def validate(self, attrs):  # noqa: PLR0912
        validated = super().validate(attrs)
        # TODO Add Bed Authorisation Validation

        if (
            not self.instance or validated.get("patient_no") != self.instance.patient_no
        ) and "suggestion" in validated:
            suggestion = validated["suggestion"]
            patient_no = validated.get("patient_no")

            if suggestion == SuggestionChoices.A and not patient_no:
                raise ValidationError(
                    {"patient_no": "This field is required for admission."}
                )

        if "suggestion" in validated and validated["suggestion"] not in [
            SuggestionChoices.DD,
            SuggestionChoices.DC,
        ]:
            treating_physician = validated.get("treating_physician")
            if not treating_physician:
                raise ValidationError(
                    {
                        "treating_physician": [
                            "This field is required as the suggestion is not 'Declared Death'"
                        ]
                    }
                )
            if treating_physician.user_type != User.TYPE_VALUE_MAP["Doctor"]:
                msg = "Only Doctors can verify a Consultation"
                raise ValidationError(msg)

            facility = (
                self.instance
                and self.instance.facility
                or validated["patient"].facility
            )
            # Check if the Doctor is associated with the Facility (.facilities)
            if not treating_physician.facilities.filter(id=facility.id).exists():
                msg = "The treating doctor is no longer linked to this facility. Please update the respective field in the form before proceeding."
                raise ValidationError(msg)

            if (
                treating_physician.home_facility
                and treating_physician.home_facility != facility
            ):
                msg = "Home Facility of the Doctor must be the same as the Consultation Facility"
                raise ValidationError(msg)

        if "suggestion" in validated and validated["suggestion"] is SuggestionChoices.R:
            if not validated.get("referred_to") and not validated.get(
                "referred_to_external"
            ):
                raise ValidationError(
                    {
                        "referred_to": [
                            f"This field is required as the suggestion is {SuggestionChoices.R}."
                        ]
                    }
                )
            if validated.get("referred_to_external"):
                validated["referred_to"] = None
            elif validated.get("referred_to"):
                validated["referred_to_external"] = None

        if (
            "action" in validated
            and validated["action"] == PatientRegistration.ActionEnum.REVIEW
        ):
            if "review_interval" not in validated:
                raise ValidationError(
                    {
                        "review_interval": [
                            "This field is required as the patient has been requested Review."
                        ]
                    }
                )
            if validated["review_interval"] <= 0:
                raise ValidationError(
                    {"review_interval": ["This field value is must be greater than 0."]}
                )

        if not self.instance and "create_diagnoses" not in validated:
            raise ValidationError({"create_diagnoses": ["This field is required."]})

        if not self.instance and "create_symptoms" not in validated:
            raise ValidationError({"create_symptoms": ["This field is required."]})

        return validated


class PatientConsultationDischargeSerializer(serializers.ModelSerializer):
    new_discharge_reason = serializers.ChoiceField(
        choices=NewDischargeReasonEnum.choices, required=True
    )
    discharge_notes = serializers.CharField(required=False, allow_blank=True)

    discharge_date = serializers.DateTimeField(required=True)
    discharge_prescription = serializers.SerializerMethodField()
    discharge_prn_prescription = serializers.SerializerMethodField()

    death_datetime = serializers.DateTimeField(required=False, allow_null=True)
    death_confirmed_doctor = serializers.CharField(required=False, allow_null=True)

    referred_to = ExternalIdSerializerField(
        queryset=Facility.objects.all(),
        required=False,
        allow_null=True,
    )
    referred_to_external = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )

    def get_discharge_prescription(self, consultation):
        return (
            Prescription.objects.filter(
                consultation=consultation,
                prescription_type=PrescriptionType.DISCHARGE.value,
            )
            .exclude(dosage_type=PrescriptionDosageType.PRN.value)
            .values()
        )

    def get_discharge_prn_prescription(self, consultation):
        return Prescription.objects.filter(
            consultation=consultation,
            prescription_type=PrescriptionType.DISCHARGE.value,
            dosage_type=PrescriptionDosageType.PRN.value,
        ).values()

    class Meta:
        model = PatientConsultation
        fields = (
            "new_discharge_reason",
            "referred_to",
            "referred_to_external",
            "discharge_notes",
            "discharge_date",
            "discharge_prescription",
            "discharge_prn_prescription",
            "death_datetime",
            "death_confirmed_doctor",
        )

    def validate(self, attrs):
        if attrs.get("referred_to") and attrs.get("referred_to_external"):
            raise ValidationError(
                {
                    "referred_to": [
                        "Only one of referred_to and referred_to_external can be set"
                    ],
                    "referred_to_external": [
                        "Only one of referred_to and referred_to_external can be set"
                    ],
                }
            )
        if attrs.get("new_discharge_reason") != NewDischargeReasonEnum.EXPIRED:
            attrs.pop("death_datetime", None)
            attrs.pop("death_confirmed_doctor", None)

        if attrs.get("new_discharge_reason") == NewDischargeReasonEnum.EXPIRED:
            if not attrs.get("death_datetime"):
                raise ValidationError({"death_datetime": "This field is required"})
            if attrs.get("death_datetime") > now():
                raise ValidationError(
                    {"death_datetime": "This field value cannot be in the future."}
                )
            if attrs.get("death_datetime") < self.instance.encounter_date:
                raise ValidationError(
                    {
                        "death_datetime": "This field value cannot be before the encounter date."
                    }
                )
            if not attrs.get("death_confirmed_doctor"):
                raise ValidationError(
                    {"death_confirmed_doctor": "This field is required"}
                )
            attrs["discharge_date"] = attrs["death_datetime"]
        elif not attrs.get("discharge_date"):
            raise ValidationError({"discharge_date": "This field is required"})
        elif attrs.get("discharge_date") > now():
            raise ValidationError(
                {"discharge_date": "This field value cannot be in the future."}
            )
        elif attrs.get("discharge_date") < self.instance.encounter_date:
            raise ValidationError(
                {
                    "discharge_date": "This field value cannot be before the encounter date."
                }
            )
        return attrs

    def update(self, instance: PatientConsultation, validated_data):
        with transaction.atomic():
            instance = super().update(instance, validated_data)
            patient: PatientRegistration = instance.patient
            patient.is_active = False
            patient.allow_transfer = True
            patient.review_time = None
            patient.save(update_fields=["allow_transfer", "is_active", "review_time"])
            ConsultationBed.objects.filter(
                consultation=self.instance, end_date__isnull=True
            ).update(end_date=now())

            return instance

    def create(self, validated_data):
        raise NotImplementedError


class PatientConsultationIDSerializer(serializers.Serializer):
    consultation_id = serializers.UUIDField(read_only=True)
    patient_id = serializers.UUIDField(read_only=True)
    bed_id = serializers.UUIDField(read_only=True)
    asset_beds = AssetBedSerializer(many=True, read_only=True)

    class Meta:
        fields = ("consultation_id", "patient_id", "bed_id", "asset_beds")


class EmailDischargeSummarySerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=False,
        help_text=(
            "Email address to send the discharge summary to. If not provided, "
            "the email address of the current user will be used."
        ),
    )

    def validate(self, attrs):
        if not attrs.get("email"):
            attrs["email"] = self.context["request"].user.email
        return attrs

    class Meta:
        model = PatientConsultation
        fields = ("email",)


class PatientConsentSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="external_id", read_only=True)
    created_by = UserBaseMinimumSerializer(read_only=True)
    archived_by = UserBaseMinimumSerializer(read_only=True)
    files = serializers.SerializerMethodField()

    class Meta:
        model = PatientConsent

        fields = (
            "id",
            "type",
            "patient_code_status",
            "files",
            "archived",
            "archived_by",
            "archived_date",
            "created_by",
            "created_date",
        )

        read_only_fields = (
            "id",
            "files",
            "created_by",
            "created_date",
            "archived",
            "archived_by",
            "archived_date",
        )

    def get_files(self, obj):
        from care.facility.api.serializers.file_upload import (
            FileUploadListSerializer,
            check_permissions,
        )

        user = self.context["request"].user
        file_type = FileUpload.FileType.CONSENT_RECORD
        if check_permissions(file_type, obj.external_id, user, "read"):
            return FileUploadListSerializer(
                FileUpload.objects.filter(
                    associating_id=obj.external_id, file_type=file_type
                ),
                many=True,
            ).data
        return None

    def validate_patient_code_status(self, value):
        if value == PatientCodeStatusType.NOT_SPECIFIED:
            msg = "Specify a correct Patient Code Status for the Consent"
            raise ValidationError(msg)
        return value

    def validate(self, attrs):
        user = self.context["request"].user
        if (
            user.user_type < User.TYPE_VALUE_MAP["DistrictAdmin"]
            and self.context["consultation"].facility_id != user.home_facility_id
        ):
            msg = "Only Home Facility Staff can create consent for a Consultation"
            raise ValidationError(msg)

        if (
            attrs.get("type", None)
            and attrs.get("type") == ConsentType.PATIENT_CODE_STATUS
            and not attrs.get("patient_code_status")
        ):
            raise ValidationError(
                {
                    "patient_code_status": [
                        "This field is required for Patient Code Status Consent"
                    ]
                }
            )

        if (
            attrs.get("type", None)
            and attrs["type"] != ConsentType.PATIENT_CODE_STATUS
            and attrs.get("patient_code_status")
        ):
            raise ValidationError(
                {
                    "patient_code_status": [
                        "This field is not required for this type of Consent"
                    ]
                }
            )
        return attrs

    def clear_existing_records(self, consultation, _type, user, self_id=None):
        consents = PatientConsent.objects.filter(
            consultation=consultation, type=_type
        ).exclude(id=self_id)

        archived_date = timezone.now()
        consents.update(
            archived=True,
            archived_by=user,
            archived_date=archived_date,
        )
        FileUpload.objects.filter(
            associating_id__in=list(consents.values_list("external_id", flat=True)),
            file_type=FileUpload.FileType.CONSENT_RECORD,
            is_archived=False,
        ).update(
            is_archived=True,
            archived_datetime=archived_date,
            archive_reason="Consent Archived",
            archived_by=user,
        )

    def create(self, validated_data):
        with transaction.atomic():
            self.clear_existing_records(
                consultation=self.context["consultation"],
                _type=validated_data["type"],
                user=self.context["request"].user,
            )
            validated_data["consultation"] = self.context["consultation"]
            validated_data["created_by"] = self.context["request"].user
            return super().create(validated_data)

    def update(self, instance, validated_data):
        with transaction.atomic():
            self.clear_existing_records(
                consultation=instance.consultation,
                _type=instance.type,
                user=self.context["request"].user,
                self_id=instance.id,
            )
            return super().update(instance, validated_data)
