from django.db.models import Q
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.api.serializers.facility import FacilityBasicInfoSerializer
from care.facility.api.serializers.patient import PatientDetailSerializer, PatientListSerializer
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
from care.facility.models.notification import Notification
from care.users.api.serializers.user import UserBaseMinimumSerializer
from care.utils.notification_handler import NotificationGenerator
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
        or (user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"] and (facility and user.state == facility.state))
    )


class ShiftingSerializer(serializers.ModelSerializer):

    id = serializers.UUIDField(source="external_id", read_only=True)

    status = ChoiceField(choices=SHIFTING_STATUS_CHOICES)
    breathlessness_level = ChoiceField(choices=BREATHLESSNESS_CHOICES, required=False)

    patient_object = PatientListSerializer(source="patient", read_only=True, required=False)

    orgin_facility_object = FacilityBasicInfoSerializer(source="orgin_facility", read_only=True, required=False)
    shifting_approving_facility_object = FacilityBasicInfoSerializer(
        source="shifting_approving_facility", read_only=True, required=False
    )
    assigned_facility_object = FacilityBasicInfoSerializer(source="assigned_facility", read_only=True, required=False)

    assigned_facility_type = ChoiceField(choices=FACILITY_TYPES, required=False)
    preferred_vehicle_choice = ChoiceField(choices=VEHICLE_CHOICES, required=False)

    orgin_facility = serializers.UUIDField(source="orgin_facility.external_id", allow_null=False, required=True)
    shifting_approving_facility = serializers.UUIDField(
        source="shifting_approving_facility.external_id", allow_null=False, required=True
    )
    assigned_facility = serializers.UUIDField(source="assigned_facility.external_id", allow_null=True, required=False)
    assigned_facility_external = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    patient = serializers.UUIDField(source="patient.external_id", allow_null=False, required=True)

    assigned_to_object = UserBaseMinimumSerializer(source="assigned_to", read_only=True)
    created_by_object = UserBaseMinimumSerializer(source="created_by", read_only=True)
    last_edited_by_object = UserBaseMinimumSerializer(source="last_edited_by", read_only=True)

    def __init__(self, instance=None, **kwargs):
        if instance:
            kwargs["partial"] = True
        super().__init__(instance=instance, **kwargs)

    def update(self, instance, validated_data):

        LIMITED_RECIEVING_STATUS_ = [
            "DESTINATION APPROVED",
            "DESTINATION REJECTED",
            "COMPLETED",
        ]
        LIMITED_RECIEVING_STATUS = [REVERSE_SHIFTING_STATUS_CHOICES[x] for x in LIMITED_RECIEVING_STATUS_]
        LIMITED_SHIFTING_STATUS_ = [
            "APPROVED",
            "REJECTED",
            "PATIENT TO BE PICKED UP",
            "TRANSPORTATION TO BE ARRANGED",
            "TRANSFER IN PROGRESS",
            "COMPLETED",
            "PENDING",
            "ON HOLD",
        ]
        LIMITED_SHIFTING_STATUS = [REVERSE_SHIFTING_STATUS_CHOICES[x] for x in LIMITED_SHIFTING_STATUS_]
        LIMITED_ORGIN_STATUS = []

        RECIEVING_REQUIRED_STATUS_ = [
            "DESTINATION APPROVED",
            "DESTINATION REJECTED",
            "TRANSPORTATION TO BE ARRANGED",
            "PATIENT TO BE PICKED UP",
            "TRANSFER IN PROGRESS",
            "COMPLETED",
        ]
        RECIEVING_REQUIRED_STATUS = [REVERSE_SHIFTING_STATUS_CHOICES[x] for x in RECIEVING_REQUIRED_STATUS_]

        user = self.context["request"].user

        if validated_data.get("assigned_facility_external"):
            validated_data["assigned_facility"] = None
        elif validated_data.get("assigned_facility"):
            validated_data["assigned_facility_external"] = None

        if "is_kasp" in validated_data:
            if validated_data["is_kasp"] != instance.is_kasp:  # Check only when changed
                if not has_facility_permission(user, instance.shifting_approving_facility):
                    raise ValidationError({"kasp": ["Permission Denied"]})

        if "status" in validated_data:
            if validated_data["status"] in LIMITED_RECIEVING_STATUS:
                if instance.assigned_facility:
                    if not has_facility_permission(user, instance.assigned_facility):
                        raise ValidationError({"status": ["Permission Denied"]})
            elif validated_data["status"] in LIMITED_SHIFTING_STATUS:
                if not has_facility_permission(user, instance.shifting_approving_facility):
                    raise ValidationError({"status": ["Permission Denied"]})

        # Dont allow editing origin or patient
        if "orgin_facility" in validated_data:
            validated_data.pop("orgin_facility")
        if "patient" in validated_data:
            validated_data.pop("patient")

        if "shifting_approving_facility" in validated_data:
            shifting_approving_facility_external_id = validated_data.pop("shifting_approving_facility")["external_id"]
            if shifting_approving_facility_external_id:
                validated_data["shifting_approving_facility_id"] = Facility.objects.get(
                    external_id=shifting_approving_facility_external_id
                ).id

        assigned = False
        if validated_data.get("assigned_facility"):
            assigned_facility_external_id = validated_data.pop("assigned_facility")["external_id"]
            if assigned_facility_external_id:
                validated_data["assigned_facility_id"] = Facility.objects.get(
                    external_id=assigned_facility_external_id
                ).id
                assigned = True
        if validated_data.get("assigned_facility_external"):
            validated_data["assigned_facility_id"] = None
            validated_data["assigned_facility_object"] = None
            assigned = True

        if "status" in validated_data:
            if validated_data["status"] in RECIEVING_REQUIRED_STATUS:
                if (not (instance.assigned_facility or instance.assigned_facility_external)) and (not assigned):
                    raise ValidationError({"status": ["Destination Facility is required for moving to this stage."]})

        instance.last_edited_by = self.context["request"].user

        old_status = instance.status

        new_instance = super().update(instance, validated_data)

        if "status" in validated_data:
            if validated_data["status"] != old_status:
                if validated_data["status"] == 40:
                    NotificationGenerator(
                        event=Notification.Event.SHIFTING_UPDATED,
                        caused_by=self.context["request"].user,
                        caused_object=ShiftingRequest.objects.get(id=new_instance.id),
                        facility=new_instance.shifting_approving_facility,
                        notification_mediums=[Notification.Medium.SYSTEM, Notification.Medium.SMS],
                    ).generate()

        return new_instance

    def create(self, validated_data):

        # Do Validity checks for each of these data
        if "status" in validated_data:
            validated_data.pop("status")

        validated_data["is_kasp"] = False

        orgin_facility_external_id = validated_data.pop("orgin_facility")["external_id"]
        # validated_data["orgin_facility_id"] = Facility.objects.get(external_id=orgin_facility_external_id).id

        shifting_approving_facility_external_id = validated_data.pop("shifting_approving_facility")["external_id"]
        validated_data["shifting_approving_facility_id"] = Facility.objects.get(
            external_id=shifting_approving_facility_external_id
        ).id

        if validated_data.get("assigned_facility_external"):
            validated_data["assigned_facility"] = None
        elif validated_data.get("assigned_facility"):
            validated_data["assigned_facility_external"] = None

        if validated_data.get("assigned_facility"):
            assigned_facility_external_id = validated_data.pop("assigned_facility")["external_id"]
            if assigned_facility_external_id:

                validated_data["assigned_facility_id"] = Facility.objects.get(
                    external_id=assigned_facility_external_id
                ).id

        patient_external_id = validated_data.pop("patient")["external_id"]
        patient = PatientRegistration.objects.get(external_id=patient_external_id)

        if patient.is_active == False:
            raise ValidationError({"patient": ["Cannot shift discharged patient"]})
        if patient.allow_transfer == False:
            patient.allow_transfer = True
            patient.save()

        validated_data["orgin_facility_id"] = patient.facility.id
        validated_data["patient_id"] = patient.id

        if ShiftingRequest.objects.filter(~Q(status__in=[30, 50, 80]), patient=patient).exists():
            raise ValidationError({"request": ["Shifting Request for Patient already exists"]})

        validated_data["created_by"] = self.context["request"].user
        validated_data["last_edited_by"] = self.context["request"].user

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
        read_only_fields = TIMESTAMP_FIELDS + ("created_by", "external_id", "id")
