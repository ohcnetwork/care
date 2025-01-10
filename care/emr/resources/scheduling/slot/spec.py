import datetime
from enum import Enum

from pydantic import UUID4
from rest_framework.exceptions import ValidationError

from care.emr.models import TokenBooking
from care.emr.models.scheduling.booking import TokenSlot
from care.emr.models.scheduling.schedule import Availability
from care.emr.resources.base import EMRResource
from care.emr.resources.patient.otp_based_flow import PatientOTPReadSpec
from care.emr.resources.user.spec import UserSpec
from care.users.models import User


class AvailabilityforTokenSpec(EMRResource):
    __model__ = Availability

    id: UUID4 | None = None
    name: str
    tokens_per_slot: int


class TokenSlotBaseSpec(EMRResource):
    __model__ = TokenSlot
    __exclude__ = ["resource", "availability"]

    id: UUID4 | None = None
    availability: UUID4
    start_datetime: datetime.datetime
    end_datetime: datetime.datetime
    allocated: int

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["availability"] = {
            "name": obj.availability.name,
            "tokens_per_slot": obj.availability.tokens_per_slot,
        }


class BookingStatusChoices(str, Enum):
    proposed = "proposed"
    pending = "pending"
    booked = "booked"
    arrived = "arrived"
    fulfilled = "fulfilled"
    cancelled = "cancelled"
    noshow = "noshow"
    entered_in_error = "entered_in_error"
    checked_in = "checked_in"
    waitlist = "waitlist"
    in_consultation = "in_consultation"


CANCELLED_STATUS_CHOICES = [
    BookingStatusChoices.entered_in_error.value,
    BookingStatusChoices.cancelled.value,
]


class TokenBookingBaseSpec(EMRResource):
    __model__ = TokenBooking
    __exclude__ = ["token_slot", "patient"]


class TokenBookingWriteSpec(TokenBookingBaseSpec):
    status: BookingStatusChoices

    def perform_extra_deserialization(self, is_update, obj):
        if self.status in CANCELLED_STATUS_CHOICES:
            raise ValidationError("Cannot cancel a booking. Use the cancel endpoint")


class TokenBookingReadSpec(TokenBookingBaseSpec):
    id: UUID4 | None = None

    token_slot: TokenSlotBaseSpec
    patient: PatientOTPReadSpec
    booked_on: datetime.datetime
    booked_by: UserSpec
    status: str
    reason_for_visit: str
    user: dict = {}

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["token_slot"] = TokenSlotBaseSpec.serialize(obj.token_slot).model_dump(
            exclude=["meta"]
        )
        mapping["patient"] = PatientOTPReadSpec.serialize(obj.patient).model_dump(
            exclude=["meta"]
        )
        mapping["user"] = UserSpec.serialize(
            User.objects.get(id=obj.token_slot.resource.user_id)
        ).model_dump(exclude=["meta"])
