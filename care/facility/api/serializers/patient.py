import datetime

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils.timezone import localtime, make_aware, now
from rest_framework import serializers

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.api.serializers.facility import (
    FacilityBasicInfoSerializer,
    FacilitySerializer,
)
from care.facility.api.serializers.patient_consultation import (
    PatientConsultationSerializer,
)
from care.facility.models import (
    DISEASE_CHOICES,
    GENDER_CHOICES,
    Disease,
    Facility,
    FacilityPatientStatsHistory,
    PatientContactDetails,
    PatientMetaInfo,
    PatientNotes,
    PatientRegistration,
    PatientSearch,
)
from care.facility.models.notification import Notification
from care.facility.models.patient_base import (
    BLOOD_GROUP_CHOICES,
    DISEASE_STATUS_CHOICES,
    DiseaseStatusEnum,
)
from care.facility.models.patient_consultation import PatientConsultation
from care.facility.models.patient_external_test import PatientExternalTest
from care.facility.models.patient_tele_consultation import PatientTeleConsultation
from care.hcx.models.claim import Claim
from care.hcx.models.policy import Policy
from care.users.api.serializers.lsg import (
    DistrictSerializer,
    LocalBodySerializer,
    StateSerializer,
    WardSerializer,
)
from care.users.api.serializers.user import UserBaseMinimumSerializer
from care.users.models import User
from care.utils.notification_handler import NotificationGenerator
from care.utils.queryset.facility import get_home_facility_queryset
from care.utils.serializer.external_id_field import ExternalIdSerializerField
from config.serializers import ChoiceField


class PatientMetaInfoSerializer(serializers.ModelSerializer):
    occupation = ChoiceField(choices=PatientMetaInfo.OccupationChoices)

    class Meta:
        model = PatientMetaInfo
        fields = "__all__"


class PatientListSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="external_id", read_only=True)
    facility = serializers.UUIDField(
        source="facility.external_id", allow_null=True, read_only=True
    )
    facility_object = FacilityBasicInfoSerializer(source="facility", read_only=True)
    ward_object = WardSerializer(source="ward", read_only=True)
    local_body_object = LocalBodySerializer(source="local_body", read_only=True)
    district_object = DistrictSerializer(source="district", read_only=True)
    state_object = StateSerializer(source="state", read_only=True)

    last_consultation = PatientConsultationSerializer(read_only=True)

    blood_group = ChoiceField(choices=BLOOD_GROUP_CHOICES, required=True)
    disease_status = ChoiceField(
        choices=DISEASE_STATUS_CHOICES, default=DiseaseStatusEnum.SUSPECTED.value
    )
    source = ChoiceField(choices=PatientRegistration.SourceChoices)

    assigned_to_object = UserBaseMinimumSerializer(source="assigned_to", read_only=True)

    # HCX
    has_eligible_policy = serializers.SerializerMethodField(
        "get_has_eligible_policy", read_only=True
    )

    def get_has_eligible_policy(self, patient):
        eligible_policies = Policy.objects.filter(
            (Q(error_text="") | Q(error_text=None)),
            outcome="complete",
            patient=patient.id,
        )
        return bool(len(eligible_policies))

    approved_claim_amount = serializers.SerializerMethodField(
        "get_approved_claim_amount", read_only=True
    )

    def get_approved_claim_amount(self, patient):
        if patient.last_consultation is not None:
            claim = (
                Claim.objects.filter(
                    Q(error_text="") | Q(error_text=None),
                    consultation__external_id=patient.last_consultation.external_id,
                    outcome="complete",
                    total_claim_amount__isnull=False,
                )
                .order_by("-modified_date")
                .first()
            )
            return claim.total_claim_amount if claim is not None else None

    class Meta:
        model = PatientRegistration
        exclude = (
            "created_by",
            "deleted",
            "ongoing_medication",
            "patient_search_id",
            "year_of_birth",
            "meta_info",
            "countries_travelled_old",
            "allergies",
            "external_id",
        )
        read_only = TIMESTAMP_FIELDS


class PatientContactDetailsSerializer(serializers.ModelSerializer):
    relation_with_patient = ChoiceField(choices=PatientContactDetails.RelationChoices)
    mode_of_contact = ChoiceField(choices=PatientContactDetails.ModeOfContactChoices)

    patient_in_contact_object = PatientListSerializer(
        read_only=True, source="patient_in_contact"
    )
    patient_in_contact = serializers.UUIDField(source="patient_in_contact.external_id")

    class Meta:
        model = PatientContactDetails
        exclude = ("patient",)

    def validate_patient_in_contact(self, value):
        if value:
            value = PatientRegistration.objects.get(external_id=value)
        return value

    def to_internal_value(self, data):
        iv = super().to_internal_value(data)
        if iv.get("patient_in_contact"):
            iv["patient_in_contact"] = iv["patient_in_contact"]["external_id"]
        return iv


class PatientDetailSerializer(PatientListSerializer):
    class MedicalHistorySerializer(serializers.Serializer):
        disease = ChoiceField(choices=DISEASE_CHOICES)
        details = serializers.CharField(required=False, allow_blank=True)

    class PatientTeleConsultationSerializer(serializers.ModelSerializer):
        class Meta:
            model = PatientTeleConsultation
            fields = "__all__"

    facility = ExternalIdSerializerField(
        queryset=Facility.objects.all(), required=False
    )
    medical_history = serializers.ListSerializer(
        child=MedicalHistorySerializer(), required=False
    )

    tele_consultation_history = serializers.ListSerializer(
        child=PatientTeleConsultationSerializer(), read_only=True
    )
    last_consultation = PatientConsultationSerializer(read_only=True)
    facility_object = FacilitySerializer(source="facility", read_only=True)
    # nearest_facility_object = FacilitySerializer(
    #     source="nearest_facility", read_only=True
    # )

    source = ChoiceField(
        choices=PatientRegistration.SourceChoices,
        default=PatientRegistration.SourceEnum.CARE.value,
    )
    disease_status = ChoiceField(
        choices=DISEASE_STATUS_CHOICES, default=DiseaseStatusEnum.SUSPECTED.value
    )

    meta_info = PatientMetaInfoSerializer(required=False, allow_null=True)
    contacted_patients = PatientContactDetailsSerializer(
        many=True, required=False, allow_null=True
    )

    test_type = ChoiceField(
        choices=PatientRegistration.TestTypeChoices,
        required=False,
        default=PatientRegistration.TestTypeEnum.UNK.value,
    )

    last_edited = UserBaseMinimumSerializer(read_only=True)
    created_by = UserBaseMinimumSerializer(read_only=True)
    vaccine_name = serializers.ChoiceField(
        choices=PatientRegistration.vaccineChoices, required=False, allow_null=True
    )

    assigned_to_object = UserBaseMinimumSerializer(source="assigned_to", read_only=True)

    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )

    allow_transfer = serializers.BooleanField(default=settings.PEACETIME_MODE)

    class Meta:
        model = PatientRegistration
        exclude = (
            "deleted",
            "patient_search_id",
            "year_of_birth",
            "countries_travelled_old",
            "external_id",
        )
        include = ("contacted_patients",)
        read_only = TIMESTAMP_FIELDS + ("last_edited", "created_by", "is_active")

    # def get_last_consultation(self, obj):
    #     last_consultation = PatientConsultation.objects.filter(patient=obj).last()
    #     if not last_consultation:
    #         return None
    #     return PatientConsultationSerializer(last_consultation).data

    # def validate_facility(self, value):
    #     if value is not None and Facility.objects.filter(external_id=value).first() is None:
    #         raise serializers.ValidationError("facility not found")
    #     return value

    def validate_countries_travelled(self, value):
        if not value:
            value = []
        if not isinstance(value, list):
            value = [value]
        return value

    def validate(self, attrs):
        validated = super().validate(attrs)
        if (
            not self.partial
            and not validated.get("age")
            and not validated.get("date_of_birth")
        ):
            raise serializers.ValidationError(
                {"non_field_errors": ["Either age or date_of_birth should be passed"]}
            )

        if validated.get("is_vaccinated"):
            if validated.get("number_of_doses") == 0:
                raise serializers.ValidationError("Number of doses cannot be 0")
            if validated.get("vaccine_name") is None:
                raise serializers.ValidationError("Vaccine name cannot be null")

        return validated

    def check_external_entry(self, srf_id):
        if srf_id:
            PatientExternalTest.objects.filter(srf_id__iexact=srf_id).update(
                patient_created=True
            )

    def create(self, validated_data):
        with transaction.atomic():
            medical_history = validated_data.pop("medical_history", [])
            meta_info = validated_data.pop("meta_info", {})
            contacted_patients = validated_data.pop("contacted_patients", [])

            if "facility" not in validated_data:
                raise serializers.ValidationError(
                    {"facility": "Facility is required to register a patient"}
                )

            # Authorization checks

            allowed_facilities = get_home_facility_queryset(
                self.context["request"].user
            )
            if not allowed_facilities.filter(
                id=self.validated_data["facility"].id
            ).exists():
                raise serializers.ValidationError(
                    {"facility": "Patient can only be created in the home facility"}
                )

            # Authorisation checks end

            if "srf_id" in validated_data:
                if validated_data["srf_id"]:
                    self.check_external_entry(validated_data["srf_id"])

            validated_data["created_by"] = self.context["request"].user
            patient = super().create(validated_data)
            diseases = []

            for disease in medical_history:
                diseases.append(Disease(patient=patient, **disease))
            if diseases:
                Disease.objects.bulk_create(diseases, ignore_conflicts=True)

            if meta_info:
                meta_info_obj = PatientMetaInfo.objects.create(**meta_info)
                patient.meta_info = meta_info_obj
                patient.save()

            if contacted_patients:
                contacted_patient_objs = [
                    PatientContactDetails(**data, patient=patient)
                    for data in contacted_patients
                ]
                PatientContactDetails.objects.bulk_create(contacted_patient_objs)

            patient.last_edited = self.context["request"].user
            patient.save()

        NotificationGenerator(
            event=Notification.Event.PATIENT_CREATED,
            caused_by=self.context["request"].user,
            caused_object=patient,
            facility=patient.facility,
        ).generate()

        return patient

    def update(self, instance, validated_data):
        with transaction.atomic():
            medical_history = validated_data.pop("medical_history", [])
            meta_info = validated_data.pop("meta_info", {})
            contacted_patients = validated_data.pop("contacted_patients", [])

            if "facility" in validated_data:
                external_id = validated_data.pop("facility")["external_id"]
                if external_id:
                    validated_data["facility_id"] = Facility.objects.get(
                        external_id=external_id
                    ).id

            if "srf_id" in validated_data:
                if instance.srf_id != validated_data["srf_id"]:
                    self.check_external_entry(validated_data["srf_id"])

            patient = super().update(instance, validated_data)
            Disease.objects.filter(patient=patient).update(deleted=True)
            diseases = []
            for disease in medical_history:
                diseases.append(Disease(patient=patient, **disease))
            if diseases:
                Disease.objects.bulk_create(diseases, ignore_conflicts=True)

            if meta_info:
                for key, value in meta_info.items():
                    setattr(patient.meta_info, key, value)
                patient.meta_info.save()

            if self.partial is not True:  # clear the list and enter details if PUT
                patient.contacted_patients.all().delete()

            if contacted_patients:
                contacted_patient_objs = [
                    PatientContactDetails(**data, patient=patient)
                    for data in contacted_patients
                ]
                PatientContactDetails.objects.bulk_create(contacted_patient_objs)

            patient.last_edited = self.context["request"].user
            patient.save()

            NotificationGenerator(
                event=Notification.Event.PATIENT_UPDATED,
                caused_by=self.context["request"].user,
                caused_object=patient,
                facility=patient.facility,
            ).generate()

            return patient


class FacilityPatientStatsHistorySerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="external_id", read_only=True)
    entry_date = serializers.DateField(
        default=make_aware(datetime.datetime.today()).date()
    )
    facility = ExternalIdSerializerField(
        queryset=Facility.objects.all(), read_only=True
    )

    class Meta:
        model = FacilityPatientStatsHistory
        exclude = (
            "deleted",
            "external_id",
        )
        read_only_fields = (
            "id",
            "facility",
        )

    def create(self, validated_data):
        instance, _ = FacilityPatientStatsHistory.objects.update_or_create(
            facility=validated_data["facility"],
            entry_date=validated_data["entry_date"],
            defaults={**validated_data, "deleted": False},
        )
        return instance


class PatientSearchSerializer(serializers.ModelSerializer):
    gender = ChoiceField(choices=GENDER_CHOICES)
    patient_id = serializers.UUIDField(source="external_id", read_only=True)

    # facility_id = serializers.UUIDField(read_only=True, allow_null=True)

    class Meta:
        model = PatientSearch
        exclude = (
            "date_of_birth",
            "year_of_birth",
            "external_id",
            "id",
        ) + TIMESTAMP_FIELDS


class PatientTransferSerializer(serializers.ModelSerializer):
    facility_object = FacilityBasicInfoSerializer(source="facility", read_only=True)
    facility = ExternalIdSerializerField(
        write_only=True, queryset=Facility.objects.all()
    )
    patient = serializers.UUIDField(source="external_id", read_only=True)

    class Meta:
        model = PatientRegistration
        fields = ("facility", "date_of_birth", "patient", "facility_object")

    def validate_date_of_birth(self, value):
        if self.instance and self.instance.date_of_birth != value:
            raise serializers.ValidationError("Date of birth does not match")
        return value

    def create(self, validated_data):
        raise NotImplementedError

    def save(self, **kwargs):
        self.instance.facility = self.validated_data["facility"]
        PatientConsultation.objects.filter(
            patient=self.instance, discharge_date__isnull=True
        ).update(discharge_date=localtime(now()))
        self.instance.save()


class PatientNotesSerializer(serializers.ModelSerializer):
    facility = FacilityBasicInfoSerializer(read_only=True)
    created_by_object = UserBaseMinimumSerializer(source="created_by", read_only=True)

    def validate_empty_values(self, data):
        if not data.get("note", "").strip():
            raise serializers.ValidationError({"note": ["Note cannot be empty"]})
        return super().validate_empty_values(data)

    class Meta:
        model = PatientNotes
        fields = ("note", "facility", "created_by_object", "created_date")
        read_only_fields = ("created_date",)
