from django.conf import settings
from django.db.models import Q
from django.utils.timezone import localtime, now
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.api.serializers.facility import FacilityBasicInfoSerializer
from care.facility.api.serializers.patient import (
    PatientDetailSerializer,
    PatientListSerializer,
)
from care.facility.models import (
    BREATHLESSNESS_CHOICES,
    FACILITY_TYPES,
    SHIFTING_STATUS_CHOICES,
    VEHICLE_CHOICES,
    Facility,
    PatientRegistration,
    ShiftingRequest,
    ShiftingRequestComment,
    User,
)
from care.facility.models.bed import ConsultationBed
from care.facility.models.notification import Notification
from care.facility.models.patient_consultation import PatientConsultation
from care.users.api.serializers.user import UserBaseMinimumSerializer
from care.utils.notification_handler import NotificationGenerator
from care.utils.serializer.external_id_field import ExternalIdSerializerField
from config.serializers import ChoiceField


def inverse_choices(choices):
    output = {}
    for choice in choices:
        output[choice[1]] = choice[0]
    return output


REVERSE_SHIFTING_STATUS_CHOICES = inverse_choices(SHIFTING_STATUS_CHOICES)


def has_facility_permission(user, facility):
    if not facility:
        return False
    return (
        user.is_superuser
        or (facility and user in facility.users.all())
        or (
            user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]
            and (facility and user.district == facility.district)
        )
        or (
            user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]
            and (facility and user.state == facility.state)
        )
    )


def discharge_patient(patient: PatientRegistration):
    current_time = localtime(now())

    patient.is_active = False
    patient.allow_transfer = True
    patient.review_time = None
    patient.save(update_fields=["allow_transfer", "is_active", "review_time"])

    last_consultation = (
        PatientConsultation.objects.filter(patient=patient).order_by("-id").first()
    )
    if last_consultation:
        reason = "REF"
        notes = "Patient Shifted to another facility"
        last_consultation.discharge_reason = reason
        last_consultation.discharge_notes = notes
        last_consultation.discharge_date = current_time
        last_consultation.current_bed = None
        last_consultation.save()

    ConsultationBed.objects.filter(
        consultation=last_consultation, end_date__isnull=True
    ).update(end_date=current_time)


class ShiftingSerializer(serializers.ModelSerializer):
    LIMITED_SHIFTING_STATUS = [
        REVERSE_SHIFTING_STATUS_CHOICES[x]
        for x in [
            "PENDING",
            "ON HOLD",
            "APPROVED",
            "REJECTED",
            # "DESTINATION APPROVED",
            # "DESTINATION REJECTED",
            "TRANSPORTATION TO BE ARRANGED",
            "PATIENT TO BE PICKED UP",
            "TRANSFER IN PROGRESS",
            "COMPLETED",
            "PATIENT EXPIRED",
            "CANCELLED",
        ]
    ]

    LIMITED_RECIEVING_STATUS = [
        REVERSE_SHIFTING_STATUS_CHOICES[x]
        for x in [
            # "PENDING",
            # "ON HOLD",
            # "APPROVED",
            # "REJECTED",
            "DESTINATION APPROVED",
            "DESTINATION REJECTED",
            # "TRANSPORTATION TO BE ARRANGED",
            # "PATIENT TO BE PICKED UP",
            # "TRANSFER IN PROGRESS",
            "COMPLETED",
            # "PATIENT EXPIRED",
            # "CANCELLED",
        ]
    ]

    PEACETIME_SHIFTING_STATUS = [
        REVERSE_SHIFTING_STATUS_CHOICES[x]
        for x in [
            # "PENDING",
            "ON HOLD",
            "APPROVED",
            "REJECTED",
            "DESTINATION APPROVED",
            "DESTINATION REJECTED",
            "TRANSPORTATION TO BE ARRANGED",
            "PATIENT TO BE PICKED UP",
            "TRANSFER IN PROGRESS",
            "COMPLETED",
            "PATIENT EXPIRED",
            "CANCELLED",
        ]
    ]

    PEACETIME_RECIEVING_STATUS = [
        REVERSE_SHIFTING_STATUS_CHOICES[x]
        for x in [
            # "PENDING",
            # "ON HOLD",
            # "APPROVED",
            # "REJECTED",
            "DESTINATION APPROVED",
            "DESTINATION REJECTED",
            # "TRANSPORTATION TO BE ARRANGED",
            # "PATIENT TO BE PICKED UP",
            # "TRANSFER IN PROGRESS",
            "COMPLETED",
            # "PATIENT EXPIRED",
            # "CANCELLED",
        ]
    ]

    RECIEVING_REQUIRED_STATUS = [
        REVERSE_SHIFTING_STATUS_CHOICES[x]
        for x in [
            "DESTINATION APPROVED",
            "DESTINATION REJECTED",
            "TRANSPORTATION TO BE ARRANGED",
            "PATIENT TO BE PICKED UP",
            "TRANSFER IN PROGRESS",
            "COMPLETED",
        ]
    ]

    id = serializers.UUIDField(source="external_id", read_only=True)

    patient = ExternalIdSerializerField(
        queryset=PatientRegistration.objects.all(),
        allow_null=False,
        required=True,
    )
    patient_object = PatientListSerializer(source="patient", read_only=True)

    status = ChoiceField(choices=SHIFTING_STATUS_CHOICES)
    breathlessness_level = ChoiceField(
        choices=BREATHLESSNESS_CHOICES, required=False, allow_null=True
    )

    orgin_facility = ExternalIdSerializerField(
        queryset=Facility.objects.all(), allow_null=False, required=True
    )
    orgin_facility_object = FacilityBasicInfoSerializer(
        source="orgin_facility", read_only=True
    )

    shifting_approving_facility = ExternalIdSerializerField(
        queryset=Facility.objects.all(), required=False
    )
    shifting_approving_facility_object = FacilityBasicInfoSerializer(
        source="shifting_approving_facility", read_only=True
    )

    assigned_facility = ExternalIdSerializerField(
        queryset=Facility.objects.all(), allow_null=True, required=False
    )
    assigned_facility_external = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    assigned_facility_object = FacilityBasicInfoSerializer(
        source="assigned_facility", read_only=True
    )

    assigned_facility_type = ChoiceField(
        choices=FACILITY_TYPES, required=False, allow_null=True
    )
    preferred_vehicle_choice = ChoiceField(
        choices=VEHICLE_CHOICES, required=False, allow_null=True
    )

    assigned_to_object = UserBaseMinimumSerializer(source="assigned_to", read_only=True)
    created_by_object = UserBaseMinimumSerializer(source="created_by", read_only=True)
    last_edited_by_object = UserBaseMinimumSerializer(
        source="last_edited_by", read_only=True
    )
    ambulance_driver_name = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )

    ambulance_number = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )

    def __init__(self, instance=None, **kwargs):
        if instance:
            kwargs["partial"] = True
        super().__init__(instance=instance, **kwargs)

    def validate_shifting_approving_facility(self, value):
        if not settings.PEACETIME_MODE and not value:
            raise ValidationError("Shifting Approving Facility is required")
        return value

    def update(self, instance, validated_data):
        if instance.status == REVERSE_SHIFTING_STATUS_CHOICES["CANCELLED"]:
            raise ValidationError("Permission Denied, Shifting request was cancelled.")
        elif instance.status == REVERSE_SHIFTING_STATUS_CHOICES["COMPLETED"]:
            raise ValidationError("Permission Denied, Shifting request was completed.")

        # Dont allow editing origin or patient
        validated_data.pop("orgin_facility")
        validated_data.pop("patient")

        user = self.context["request"].user

        if validated_data.get("assigned_facility_external"):
            validated_data["assigned_facility"] = None
            validated_data["assigned_facility_id"] = None
            validated_data["assigned_facility_object"] = None
        elif validated_data.get("assigned_facility"):
            validated_data["assigned_facility_external"] = None

        if (
            "is_kasp" in validated_data
            and validated_data["is_kasp"] != instance.is_kasp  # check only when changed
            and not has_facility_permission(user, instance.shifting_approving_facility)
        ):
            raise ValidationError({"kasp": ["Permission Denied"]})

        if "status" in validated_data:
            status = validated_data["status"]
            if status == REVERSE_SHIFTING_STATUS_CHOICES[
                "CANCELLED"
            ] and not has_facility_permission(user, instance.orgin_facility):
                raise ValidationError({"status": ["Permission Denied"]})

            if settings.PEACETIME_MODE:
                if (
                    status in self.PEACETIME_SHIFTING_STATUS
                    and has_facility_permission(user, instance.orgin_facility)
                ):
                    pass
                elif (
                    status in self.PEACETIME_RECIEVING_STATUS
                    and has_facility_permission(user, instance.assigned_facility)
                ):
                    pass
                else:
                    raise ValidationError({"status": ["Permission Denied"]})

            elif (
                status in self.LIMITED_RECIEVING_STATUS
                and instance.assigned_facility
                and not has_facility_permission(user, instance.assigned_facility)
            ):
                raise ValidationError({"status": ["Permission Denied"]})

            elif status in self.LIMITED_SHIFTING_STATUS and not has_facility_permission(
                user, instance.shifting_approving_facility
            ):
                raise ValidationError({"status": ["Permission Denied"]})

        assigned = bool(
            validated_data.get("assigned_facility")
            or validated_data.get("assigned_facility_external")
        )

        if (
            "status" in validated_data
            and validated_data["status"] in self.RECIEVING_REQUIRED_STATUS
            and (
                not (instance.assigned_facility or instance.assigned_facility_external)
            )
            and (not assigned)
        ):
            raise ValidationError(
                {
                    "status": [
                        "Destination Facility is required for moving to this stage."
                    ]
                }
            )

        validated_data["last_edited_by"] = self.context["request"].user

        if (
            "status" in validated_data
            and validated_data["status"] == REVERSE_SHIFTING_STATUS_CHOICES["COMPLETED"]
        ):
            discharge_patient(instance.patient)

        old_status = instance.status
        new_instance = super().update(instance, validated_data)

        patient = new_instance.patient
        patient.last_consultation.category = self.initial_data["patient_category"]
        patient.last_consultation.save()

        if (
            "status" in validated_data
            and validated_data["status"] != old_status
            and validated_data["status"] == 40
        ):
            NotificationGenerator(
                event=Notification.Event.SHIFTING_UPDATED,
                caused_by=self.context["request"].user,
                caused_object=new_instance,
                facility=new_instance.shifting_approving_facility,
                notification_mediums=[
                    Notification.Medium.SYSTEM,
                    Notification.Medium.SMS,
                ],
            ).generate()

        return new_instance

    def create(self, validated_data):
        # Do Validity checks for each of these data
        if "status" in validated_data:
            validated_data.pop("status")

        if settings.PEACETIME_MODE:
            # approve the request by default if in peacetime mode
            validated_data["status"] = 20

        assigned = bool(
            validated_data.get("assigned_facility")
            or validated_data.get("assigned_facility_external")
        )
        if (
            "status" in validated_data
            and validated_data["status"] in self.RECIEVING_REQUIRED_STATUS
            and (not assigned)
        ):
            raise ValidationError(
                {
                    "status": [
                        "Destination Facility is required for moving to this stage."
                    ]
                }
            )

        validated_data["is_kasp"] = False

        patient = validated_data["patient"]
        if ShiftingRequest.objects.filter(
            ~Q(status__in=[30, 50, 80, 100]), patient=patient
        ).exists():
            raise ValidationError(
                {"request": ["Shifting Request for Patient already exists"]}
            )

        if not patient.is_active:
            raise ValidationError({"patient": ["Cannot shift discharged patient"]})
        if not patient.allow_transfer:
            patient.allow_transfer = True
            patient.save()

        if patient.last_consultation:
            patient.last_consultation.category = self.initial_data["patient_category"]
            patient.last_consultation.save()

        validated_data["orgin_facility"] = patient.facility

        validated_data["created_by"] = self.context["request"].user
        validated_data["last_edited_by"] = self.context["request"].user

        if (
            "status" in validated_data
            and validated_data["status"] == REVERSE_SHIFTING_STATUS_CHOICES["COMPLETED"]
        ):
            discharge_patient(patient)

        return super().create(validated_data)

    class Meta:
        model = ShiftingRequest
        exclude = ("deleted",)
        read_only_fields = TIMESTAMP_FIELDS


class ShiftingDetailSerializer(ShiftingSerializer):
    patient = PatientDetailSerializer(read_only=True, required=False)

    class Meta:
        model = ShiftingRequest
        exclude = ("deleted",)
        read_only_fields = TIMESTAMP_FIELDS


class ShiftingRequestCommentSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)

    created_by_object = UserBaseMinimumSerializer(source="created_by", read_only=True)

    def validate_empty_values(self, data):
        if not data.get("comment", "").strip():
            raise serializers.ValidationError({"comment": ["Comment cannot be empty"]})
        return super().validate_empty_values(data)

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user

        return super().create(validated_data)

    class Meta:
        model = ShiftingRequestComment
        exclude = ("deleted", "request")
        read_only_fields = TIMESTAMP_FIELDS + (
            "created_by",
            "external_id",
            "id",
        )
