from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from django.core.cache.backends.locmem import LocMemCache
from django.urls import reverse
from django.utils import timezone

from care.emr.models.scheduling.booking import TokenBooking, TokenSlot
from care.emr.models.scheduling.schedule import (
    Availability,
    SchedulableResource,
    Schedule,
)
from care.emr.models.tag_config import TagConfig, TagDeleteRequest
from care.utils.tests.base import CareAPITestBase


class BookingTagExpiryTests(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_super_user()
        self.client.force_authenticate(self.user)
        self.facility = self.create_facility(self.user)
        self.patient = self.create_patient()
        self.now = timezone.now()
        clock = patch("care.emr.tagging.base.care_now", return_value=self.now)
        clock.start()
        self.addCleanup(clock.stop)
        action_cache = patch(
            "care.emr.models.action.cache", LocMemCache(str(uuid4()), {})
        )
        action_cache.start()
        self.addCleanup(action_cache.stop)
        self.resource = SchedulableResource.objects.create(
            resource_type="practitioner", user=self.user, facility=self.facility
        )
        self.schedule = Schedule.objects.create(
            name="Clinic",
            resource=self.resource,
            valid_from=self.now,
            valid_to=self.now + timedelta(days=1),
            is_public=True,
        )
        self.availability = Availability.objects.create(
            schedule=self.schedule,
            name="Morning clinic",
            slot_type="appointment",
            slot_size_in_minutes=30,
            tokens_per_slot=1,
            availability=[],
        )
        self.slot = self.make_slot()
        self.tag = self.make_tag()

    def make_slot(self):
        return TokenSlot.objects.create(
            resource=self.resource,
            availability=self.availability,
            start_datetime=self.now + timedelta(hours=1),
            end_datetime=self.now + timedelta(hours=2),
        )

    def make_tag(self, **kwargs):
        return TagConfig.objects.create(
            **{
                "display": "Follow up",
                "status": "active",
                "resource": "token_booking",
                "category": "clinical",
                "facility": self.facility,
                "expiry_metadata": {"modification_allowed": True},
                **kwargs,
            }
        )

    def tag_request(self, tag=None):
        return {
            "tag": str((tag or self.tag).external_id),
            "expiry_offset": {"minutes": 30},
        }

    def create_url(self):
        return reverse(
            "slot-create-appointment",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": self.slot.external_id,
            },
        )

    def reschedule(self, original, new_slot, tag):
        return self.client.post(
            reverse(
                "appointments-reschedule",
                kwargs={
                    "facility_external_id": self.facility.external_id,
                    "external_id": original.external_id,
                },
            ),
            {
                "new_slot": str(new_slot.external_id),
                "new_booking_note": "Moved appointment",
                "tags": [self.tag_request(tag)],
            },
            format="json",
        )

    def original_booking(self):
        booking = TokenBooking.objects.create(
            token_slot=self.slot,
            patient=self.patient,
            booked_by=self.user,
            status="booked",
            note="Original appointment",
        )
        self.slot.allocated = 1
        self.slot.save(update_fields=["allocated"])
        return booking

    def assert_tag_expiry(self, booking):
        booking.refresh_from_db()
        self.assertEqual(booking.tags, [self.tag.id])
        expiry = self.now + timedelta(minutes=30)
        self.assertEqual(booking.tags_data, {str(self.tag.id): {"expiry": str(expiry)}})
        scheduled = TagDeleteRequest.objects.get(
            resource_type="token_booking", resource_id=booking.pk, tag_config=self.tag
        )
        self.assertEqual(scheduled.trigger_at, expiry)

    def test_creating_appointment_accepts_structured_tags_and_schedules_expiry(self):
        response = self.client.post(
            self.create_url(),
            {
                "patient": str(self.patient.external_id),
                "note": "Follow up",
                "tags": [self.tag_request()],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        booking = TokenBooking.objects.get(external_id=response.data["id"])
        self.assert_tag_expiry(booking)
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.allocated, 1)

    def test_invalid_tag_rolls_back_appointment_and_capacity_reservation(self):
        wrong_tag = self.make_tag(resource="patient")
        response = self.client.post(
            self.create_url(),
            {
                "patient": str(self.patient.external_id),
                "note": "Follow up",
                "tags": [self.tag_request(wrong_tag)],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.allocated, 0)
        self.assertFalse(TokenBooking.objects.exists())
        self.assertFalse(TagDeleteRequest.objects.exists())

    def test_rescheduling_applies_structured_tag_expiry_to_the_new_booking(self):
        original = self.original_booking()
        new_slot = self.make_slot()
        response = self.reschedule(original, new_slot, self.tag)
        self.assertEqual(response.status_code, 200, response.data)
        new_booking = TokenBooking.objects.get(external_id=response.data["id"])
        self.assert_tag_expiry(new_booking)
        self.assertEqual(new_booking.note, "Moved appointment")
        original.refresh_from_db()
        self.assertEqual(original.status, "rescheduled")
        self.assertEqual(original.tags, [])
        self.slot.refresh_from_db()
        new_slot.refresh_from_db()
        self.assertEqual(self.slot.allocated, 0)
        self.assertEqual(new_slot.allocated, 1)

    def test_invalid_reschedule_tag_preserves_original_booking_and_both_slots(self):
        original = self.original_booking()
        new_slot = self.make_slot()
        response = self.reschedule(
            original, new_slot, self.make_tag(resource="patient")
        )
        self.assertEqual(response.status_code, 400, response.data)
        original.refresh_from_db()
        self.assertEqual(original.status, "booked")
        self.assertEqual(original.note, "Original appointment")
        self.slot.refresh_from_db()
        new_slot.refresh_from_db()
        self.assertEqual(self.slot.allocated, 1)
        self.assertEqual(new_slot.allocated, 0)
        self.assertEqual(TokenBooking.objects.count(), 1)
        self.assertFalse(TagDeleteRequest.objects.exists())
