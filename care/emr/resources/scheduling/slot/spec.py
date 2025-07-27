import datetime
from enum import Enum

from pydantic import UUID4
from rest_framework.exceptions import ValidationError

from care.emr.models import TokenBooking
from care.emr.models.scheduling.booking import TokenSlot
from care.emr.resources.base import EMRResource, model_from_cache
from care.emr.resources.facility.spec import FacilityBareMinimumSpec
from care.emr.resources.patient.otp_based_flow import PatientOTPReadSpec
from care.emr.resources.user.spec import UserSpec
from care.emr.tagging.base import SingleFacilityTagManager


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
    rescheduled = "rescheduled"


CANCELLED_STATUS_CHOICES = [
    BookingStatusChoices.entered_in_error.value,
    BookingStatusChoices.cancelled.value,
    BookingStatusChoices.rescheduled.value,
]

COMPLETED_STATUS_CHOICES = [
    BookingStatusChoices.fulfilled.value,
    BookingStatusChoices.noshow.value,
    BookingStatusChoices.entered_in_error.value,
    BookingStatusChoices.cancelled.value,
    BookingStatusChoices.rescheduled.value,
]


class TokenBookingBaseSpec(EMRResource):
    __model__ = TokenBooking
    __exclude__ = ["token_slot", "patient"]


class TokenBookingWriteSpec(TokenBookingBaseSpec):
    status: BookingStatusChoices
    note: str

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
    note: str
    user: dict = {}
    facility: dict = {}
    created_by: UserSpec | None = None
    updated_by: UserSpec | None = None
    created_date: datetime.datetime
    modified_date: datetime.datetime

    tags: list[dict] = []

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["token_slot"] = TokenSlotBaseSpec.serialize(obj.token_slot).model_dump(
            exclude=["meta"]
        )
        mapping["patient"] = PatientOTPReadSpec.serialize(obj.patient).model_dump(
            exclude=["meta"]
        )
        mapping["user"] = model_from_cache(UserSpec, id=obj.token_slot.resource.user_id)
        mapping["facility"] = model_from_cache(
            FacilityBareMinimumSpec, id=obj.token_slot.resource.facility_id
        )
        mapping["tags"] = SingleFacilityTagManager().render_tags(obj)
        if obj.booked_by_id:
            mapping["booked_by"] = model_from_cache(UserSpec, id=obj.booked_by_id)

        cls.serialize_audit_users(mapping, obj)
