from rest_framework import serializers

from care.facility.api.serializers.patient import PatientListSerializer
from care.facility.api.serializers.schedule import ScheduleResourceSerializer
from care.facility.models.appointment import TokenBooking, TokenSlot
from care.facility.models.patient import PatientRegistration
from care.facility.models.schedule import SchedulableResource
from care.users.api.serializers.user import UserBaseMinimumSerializer


class DateTimeRangeQuerySerializer(serializers.Serializer):
    valid_from = serializers.DateTimeField()
    valid_to = serializers.DateTimeField()


class DateRangeQuerySerializer(serializers.Serializer):
    valid_from = serializers.DateField()
    valid_to = serializers.DateField()


class TokenSlotReadOnlySerializer(serializers.Serializer):
    id = serializers.CharField(source="external_id")
    resource = ScheduleResourceSerializer()
    start_datetime = serializers.DateTimeField()
    end_datetime = serializers.DateTimeField()
    tokens_count = serializers.IntegerField()
    tokens_remaining = serializers.IntegerField()

    class Meta:
        model = TokenSlot


class AppointmentBookingReadOnlySerializer(serializers.Serializer):
    id = serializers.CharField(source="external_id")
    patient = PatientListSerializer()
    resource = ScheduleResourceSerializer(source="token_slot.resource")
    token_slot = TokenSlotReadOnlySerializer()
    reason_for_visit = serializers.CharField()

    class Meta:
        model = TokenBooking


class AppointmentBookingSerializer(serializers.Serializer):
    patient = serializers.UUIDField()
    resource = serializers.UUIDField()
    slot_start = serializers.DateTimeField()
    reason_for_visit = serializers.CharField()

    def validate_patient(self, value):
        try:
            return PatientRegistration.objects.get(external_id=value)
        except PatientRegistration.DoesNotExist as e:
            msg = "Patient not found"
            raise serializers.ValidationError(msg) from e

    def validate_resource(self, value):
        try:
            return SchedulableResource.objects.get(external_id=value)
        except SchedulableResource.DoesNotExist as e:
            msg = "Resource not found"
            raise serializers.ValidationError(msg) from e

    def to_representation(self, instance):
        return AppointmentBookingReadOnlySerializer(instance).data


class AvailableDoctorsSerializer(UserBaseMinimumSerializer):
    pass
