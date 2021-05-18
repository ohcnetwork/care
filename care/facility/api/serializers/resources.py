from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.api.serializers.facility import FacilityBasicInfoSerializer
from care.facility.models import RESOURCE_CATEGORY_CHOICES, RESOURCE_STATUS_CHOICES, Facility, ResourceRequest, User
from care.users.api.serializers.user import UserBaseMinimumSerializer
from config.serializers import ChoiceField


def inverse_choices(choices):
    output = {}
    for choice in choices:
        output[choice[1]] = choice[0]
    return output


REVERSE_SHIFTING_STATUS_CHOICES = inverse_choices(RESOURCE_STATUS_CHOICES)


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


class ResourceRequestSerializer(serializers.ModelSerializer):

    id = serializers.UUIDField(source="external_id", read_only=True)

    status = ChoiceField(choices=RESOURCE_STATUS_CHOICES)

    orgin_facility_object = FacilityBasicInfoSerializer(source="orgin_facility", read_only=True, required=False)
    approving_facility_object = FacilityBasicInfoSerializer(
        source="shifting_approving_facility", read_only=True, required=False
    )
    assigned_facility_object = FacilityBasicInfoSerializer(source="assigned_facility", read_only=True, required=False)

    category = ChoiceField(choices=RESOURCE_CATEGORY_CHOICES)

    orgin_facility = serializers.UUIDField(source="orgin_facility.external_id", allow_null=False, required=True)
    approving_facility = serializers.UUIDField(
        source="shifting_approving_facility.external_id", allow_null=False, required=True
    )
    assigned_facility = serializers.UUIDField(source="assigned_facility.external_id", allow_null=True, required=False)

    assigned_to_object = UserBaseMinimumSerializer(source="assigned_to", read_only=True)
    created_by_object = UserBaseMinimumSerializer(source="created_by", read_only=True)
    last_edited_by_object = UserBaseMinimumSerializer(source="last_edited_by", read_only=True)

    def __init__(self, instance=None, **kwargs):
        if instance:
            kwargs["partial"] = True
        super().__init__(instance=instance, **kwargs)

    def update(self, instance, validated_data):

        LIMITED_RECIEVING_STATUS_ = []
        LIMITED_RECIEVING_STATUS = [REVERSE_SHIFTING_STATUS_CHOICES[x] for x in LIMITED_RECIEVING_STATUS_]
        LIMITED_SHIFTING_STATUS_ = [
            "ON HOLD",
            "APPROVED",
            "REJECTED",
            "TRANSPORTATION TO BE ARRANGED",
            "TRANSFER IN PROGRESS",
            "COMPLETED",
        ]
        LIMITED_SHIFTING_STATUS = [REVERSE_SHIFTING_STATUS_CHOICES[x] for x in LIMITED_SHIFTING_STATUS_]
        LIMITED_ORGIN_STATUS = []

        user = self.context["request"].user

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

        if "shifting_approving_facility" in validated_data:
            shifting_approving_facility_external_id = validated_data.pop("shifting_approving_facility")["external_id"]
            if shifting_approving_facility_external_id:
                validated_data["shifting_approving_facility_id"] = Facility.objects.get(
                    external_id=shifting_approving_facility_external_id
                ).id

        if "assigned_facility" in validated_data:
            assigned_facility_external_id = validated_data.pop("assigned_facility")["external_id"]
            if assigned_facility_external_id:
                validated_data["assigned_facility_id"] = Facility.objects.get(
                    external_id=assigned_facility_external_id
                ).id

        instance.last_edited_by = self.context["request"].user

        new_instance = super().update(instance, validated_data)

        return new_instance

    def create(self, validated_data):

        # Do Validity checks for each of these data
        if "status" in validated_data:
            validated_data.pop("status")

        validated_data["is_kasp"] = False

        orgin_facility_external_id = validated_data.pop("orgin_facility")["external_id"]
        validated_data["orgin_facility_id"] = Facility.objects.get(external_id=orgin_facility_external_id).id

        shifting_approving_facility_external_id = validated_data.pop("shifting_approving_facility")["external_id"]
        validated_data["shifting_approving_facility_id"] = Facility.objects.get(
            external_id=shifting_approving_facility_external_id
        ).id

        if "assigned_facility" in validated_data:
            assigned_facility_external_id = validated_data.pop("assigned_facility")["external_id"]
            if assigned_facility_external_id:

                validated_data["assigned_facility_id"] = Facility.objects.get(
                    external_id=assigned_facility_external_id
                ).id

        validated_data["created_by"] = self.context["request"].user
        validated_data["last_edited_by"] = self.context["request"].user

        return super().create(validated_data)

    class Meta:
        model = ResourceRequest
        exclude = ("deleted",)
        read_only_fields = TIMESTAMP_FIELDS

