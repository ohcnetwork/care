from django.contrib.contenttypes.models import ContentType
from psycopg.types.range import Range
from rest_framework import serializers

from care.facility.models.facility import Facility, FacilityUser
from care.facility.models.schedule import (
    REVERSE_SLOT_TYPE,
    Availability,
    SchedulableResource,
    Schedule,
    ScheduleException,
    SlotType,
)
from care.users.models import User

MONDAY = 1
SUNDAY = 7


class SimpleFacilitySerializer(serializers.Serializer):
    id = serializers.IntegerField(source="external_id")
    name = serializers.CharField()


class ScheduleResourceSerializer(serializers.Serializer):
    id = serializers.IntegerField(source="resource.external_id")
    facility = SimpleFacilitySerializer()

    def to_representation(self, instance: SchedulableResource) -> dict[str, any]:
        if ContentType.objects.get_for_model(User) == instance.resource_type:
            return {
                "id": instance.resource.external_id,
                "name": instance.resource.full_name,
            }
        return super().to_representation(instance)


class AvailabilityReadOnlySerializer(serializers.Serializer):
    id = serializers.IntegerField(source="external_id")
    name = serializers.CharField()
    slot_type = serializers.ChoiceField(choices=SlotType.choices)
    slot_size_in_minutes = serializers.IntegerField()
    tokens_per_slot = serializers.IntegerField()
    days_of_week = serializers.ListField(child=serializers.IntegerField())
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()


class ScheduleReadOnlySerializer(serializers.Serializer):
    id = serializers.IntegerField(source="external_id")
    resource = ScheduleResourceSerializer()
    name = serializers.CharField()
    valid_from = serializers.DateTimeField()
    valid_to = serializers.DateTimeField()
    availability = AvailabilityReadOnlySerializer(many=True, source="availability_set")

    class Meta:
        model = Schedule


class AvailabilityCreateSerializer(serializers.ModelSerializer):
    slot_type = serializers.ChoiceField(choices=SlotType.labels)

    class Meta:
        model = Availability
        fields = (
            "external_id",
            "name",
            "slot_type",
            "slot_size_in_minutes",
            "tokens_per_slot",
            "days_of_week",
            "start_time",
            "end_time",
        )

    def validate_slot_type(self, value):
        return REVERSE_SLOT_TYPE[value]

    def validate_days_of_week(self, value):
        # validate that days of week is a list of integers between 1 and 7
        # iso weekday is 1 (monday) to 7 (sunday)
        if not all(MONDAY <= day <= SUNDAY for day in value):
            msg = "Days of week must be a list of integers between 1 and 7"
            raise serializers.ValidationError(msg)
        return value


class ScheduleCreateSerializer(serializers.ModelSerializer):
    doctor_username = serializers.CharField(required=False)
    availability = AvailabilityCreateSerializer(many=True)

    class Meta:
        model = Schedule
        fields = (
            "doctor_username",
            "name",
            "valid_from",
            "valid_to",
            "availability",
        )

    def validate_doctor_username(self, value):
        if not FacilityUser.objects.filter(
            user__username=value,
            facility__external_id=self.context["request"].parser_context["kwargs"][
                "facility_external_id"
            ],
        ).exists():
            msg = "Doctor not found for this facility"
            raise serializers.ValidationError(msg)
        return value

    def create(self, validated_data: dict) -> Schedule:
        if doctor_username := validated_data.pop("doctor_username", None):
            facility = Facility.objects.get(
                external_id=self.context["request"].parser_context["kwargs"][
                    "facility_external_id"
                ]
            )
            doctor = FacilityUser.objects.get(
                user__username=doctor_username, facility=facility
            ).user

            user_content_type = ContentType.objects.get_for_model(doctor)
            resource, _ = SchedulableResource.objects.get_or_create(
                facility=facility,
                resource_id=doctor.id,
                resource_type=user_content_type,
            )
            validated_data["resource"] = resource

        availability_data = validated_data.pop("availability")
        schedule = super().create(validated_data)
        for availability in availability_data:
            availability["schedule"] = schedule
            Availability.objects.create(**availability)
        return schedule

    def to_representation(self, instance: Schedule) -> dict[str, any]:
        return ScheduleReadOnlySerializer(instance).data


class AvailabilityUpdateSerializer(serializers.ModelSerializer):
    external_id = serializers.UUIDField(required=False)

    class Meta:
        model = Availability
        fields = (
            "external_id",
            "name",
            "slot_type",
            "slot_size_in_minutes",
            "tokens_per_slot",
            "days_of_week",
            "start_time",
            "end_time",
        )

    def validate_days_of_week(self, value):
        # validate that days of week is a list of integers between 1 and 7
        # iso weekday is 1 (monday) to 7 (sunday)
        if not all(MONDAY <= day <= SUNDAY for day in value):
            msg = "Days of week must be a list of integers between 1 and 7"
            raise serializers.ValidationError(msg)
        return value


class ScheduleUpdateSerializer(serializers.ModelSerializer):
    availability = AvailabilityUpdateSerializer(many=True)

    class Meta:
        model = Schedule
        fields = (
            "name",
            "valid_from",
            "valid_to",
            "availability",
        )

    def update(self, instance, validated_data):
        availability_data = validated_data.pop("availability", [])
        schedule = super().update(instance, validated_data)

        for availability in availability_data:
            if external_id := availability.pop("external_id", None):
                Availability.objects.filter(
                    external_id=external_id, schedule=schedule
                ).update(**availability)
            else:
                availability["schedule"] = schedule
                Availability.objects.create(**availability)

        return schedule

    def to_representation(self, instance: Schedule) -> dict[str, any]:
        return ScheduleReadOnlySerializer(instance).data


class ScheduleExceptionReadOnlySerializer(serializers.Serializer):
    id = serializers.IntegerField(source="external_id")
    name = serializers.CharField()
    is_available = serializers.BooleanField()
    slot_type = serializers.ChoiceField(choices=SlotType.choices)
    slot_size_in_minutes = serializers.IntegerField()
    tokens_per_slot = serializers.IntegerField()

    def to_representation(self, instance: ScheduleException) -> dict[str, any]:
        data = super().to_representation(instance)
        if isinstance(instance.datetime_range, list):
            data["datetime_range"] = instance.datetime_range
        elif isinstance(instance.datetime_range, Range):
            data["datetime_range"] = [
                instance.datetime_range.lower,
                instance.datetime_range.upper,
            ]
        else:
            msg = f"Invalid datetime_range type: {type(instance.datetime_range)}"
            raise ValueError(msg)
        return data


class ScheduleExceptionCreateSerializer(serializers.ModelSerializer):
    doctor_username = serializers.CharField(required=False)
    datetime_range = serializers.ListField(child=serializers.DateTimeField())

    class Meta:
        model = ScheduleException
        fields = (
            "doctor_username",
            "name",
            "is_available",
            "datetime_range",
            "slot_type",
            "slot_size_in_minutes",
            "tokens_per_slot",
        )

    def validate_doctor_username(self, value):
        if not FacilityUser.objects.filter(
            user__username=value,
            facility__external_id=self.context["request"].parser_context["kwargs"][
                "facility_external_id"
            ],
        ).exists():
            msg = "Doctor not found for this facility"
            raise serializers.ValidationError(msg)
        return value

    def create(self, validated_data):
        if doctor_username := validated_data.pop("doctor_username", None):
            facility = Facility.objects.get(
                external_id=self.context["request"].parser_context["kwargs"][
                    "facility_external_id"
                ]
            )
            doctor = FacilityUser.objects.get(
                user__username=doctor_username, facility=facility
            ).user

            user_content_type = ContentType.objects.get_for_model(doctor)
            resource, _ = SchedulableResource.objects.get_or_create(
                facility=facility,
                resource_id=doctor.id,
                resource_type=user_content_type,
            )
            validated_data["resource"] = resource

        return super().create(validated_data)

    def to_representation(self, instance: ScheduleException) -> dict[str, any]:
        return ScheduleExceptionReadOnlySerializer(instance).data


class ScheduleExceptionUpdateSerializer(serializers.ModelSerializer):
    datetime_range = serializers.ListField(child=serializers.DateTimeField())

    class Meta:
        model = ScheduleException
        fields = (
            "name",
            "is_available",
            "datetime_range",
            "slot_type",
            "slot_size_in_minutes",
            "tokens_per_slot",
        )

    def to_representation(self, instance: ScheduleException) -> dict[str, any]:
        return ScheduleExceptionReadOnlySerializer(instance).data
