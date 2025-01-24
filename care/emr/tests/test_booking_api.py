from datetime import UTC, datetime, timedelta

from django.test.utils import ignore_warnings
from django.urls import reverse

from care.emr.models import (
    Availability,
    AvailabilityException,
    SchedulableUserResource,
    Schedule,
    TokenBooking,
    TokenSlot,
)
from care.emr.resources.scheduling.schedule.spec import SlotTypeOptions
from care.emr.resources.scheduling.slot.spec import (
    CANCELLED_STATUS_CHOICES,
    BookingStatusChoices,
)
from care.security.permissions.user_schedule import UserSchedulePermissions
from care.utils.tests.base import CareAPITestBase
from config.patient_otp_authentication import PatientOtpObject


@ignore_warnings(category=RuntimeWarning, message=r".*received a naive datetime.*")
class TestBookingViewSet(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.patient = self.create_patient()
        self.resource = SchedulableUserResource.objects.create(
            user=self.user,
            facility=self.facility,
        )
        self.schedule = Schedule.objects.create(
            resource=self.resource,
            name="Test Schedule",
            valid_from=datetime.now(UTC) - timedelta(days=30),
            valid_to=datetime.now(UTC) + timedelta(days=30),
        )
        self.availability = Availability.objects.create(
            schedule=self.schedule,
            name="Test Availability",
            slot_type=SlotTypeOptions.appointment.value,
            slot_size_in_minutes=120,
            tokens_per_slot=30,
            create_tokens=False,
            reason="",
            availability=[
                {"day_of_week": 0, "start_time": "09:00:00", "end_time": "13:00:00"},
                {"day_of_week": 1, "start_time": "09:00:00", "end_time": "13:00:00"},
                {"day_of_week": 2, "start_time": "09:00:00", "end_time": "13:00:00"},
                {"day_of_week": 3, "start_time": "09:00:00", "end_time": "13:00:00"},
                {"day_of_week": 4, "start_time": "09:00:00", "end_time": "13:00:00"},
                {"day_of_week": 5, "start_time": "09:00:00", "end_time": "13:00:00"},
                {"day_of_week": 6, "start_time": "09:00:00", "end_time": "13:00:00"},
            ],
        )
        self.slot = self.create_slot()
        self.client.force_authenticate(user=self.user)

        self.base_url = reverse(
            "appointments-list",
            kwargs={"facility_external_id": self.facility.external_id},
        )

    def _get_booking_url(self, booking_id):
        """Helper to get the detail URL for a specific booking."""
        return reverse(
            "appointments-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": booking_id,
            },
        )

    def create_booking(self, **kwargs):
        data = {
            "token_slot": self.slot,
            "patient": self.patient,
            "booked_by": self.user,
            "status": BookingStatusChoices.booked.value,
        }
        data.update(kwargs)
        if data["status"] not in CANCELLED_STATUS_CHOICES:
            slot = data["token_slot"]
            slot.allocated += 1
            slot.save()
        return TokenBooking.objects.create(**data)

    def create_slot(self, **kwargs):
        data = {
            "resource": self.resource,
            "availability": self.availability,
            "start_datetime": datetime.now(UTC) + timedelta(minutes=30),
            "end_datetime": datetime.now(UTC) + timedelta(minutes=60),
            "allocated": 0,
        }
        data.update(kwargs)
        return TokenSlot.objects.create(**data)

    def test_list_booking_with_permissions(self):
        """Users with can_list_user_booking permission can list bookings."""
        permissions = [UserSchedulePermissions.can_list_user_booking.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)

    def test_list_booking_without_permissions(self):
        """Users without can_list_user_booking permission cannot list bookings."""
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 403)

    def test_list_booking_filtered_by_schedulable_user(self):
        """Users can list bookings filtered by schedulable user resource."""
        permissions = [UserSchedulePermissions.can_list_user_booking.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        self.create_booking()

        response = self.client.get(self.base_url, data={"user": self.user.external_id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)

    def test_list_booking_filtered_by_non_schedulable_user(self):
        """Users can list bookings filtered by non-schedulable user resource, but it'd be empty queryset."""
        permissions = [UserSchedulePermissions.can_list_user_booking.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        non_schedulable_user = self.create_user()
        response = self.client.get(
            self.base_url, data={"user": non_schedulable_user.external_id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 0)

    def test_retrieve_booking_with_permissions(self):
        """Users with can_list_user_booking permission can retrieve bookings."""
        permissions = [UserSchedulePermissions.can_list_user_booking.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        booking = self.create_booking()
        response = self.client.get(self._get_booking_url(booking.external_id))
        self.assertEqual(response.status_code, 200)

    def test_retrieve_booking_without_permissions(self):
        """Users without can_list_user_booking permission cannot retrieve bookings."""
        booking = self.create_booking()
        response = self.client.get(self._get_booking_url(booking.external_id))
        self.assertEqual(response.status_code, 403)

    def test_update_with_permissions(self):
        """Users with can_write_user_booking permission can update bookings."""
        permissions = [
            UserSchedulePermissions.can_write_user_booking.name,
            UserSchedulePermissions.can_list_user_booking.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        booking = self.create_booking()
        update_data = {
            "status": BookingStatusChoices.checked_in.value,
        }
        response = self.client.put(
            self._get_booking_url(booking.external_id), update_data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], BookingStatusChoices.checked_in.value)

    def test_update_without_permissions(self):
        """Users without can_write_user_booking permission cannot update bookings."""
        permissions = [
            UserSchedulePermissions.can_list_user_booking.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

    def test_cancel_booking_via_update(self):
        """Users cannot cancel bookings via update."""
        permissions = [
            UserSchedulePermissions.can_write_user_booking.name,
            UserSchedulePermissions.can_list_user_booking.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        booking = self.create_booking()
        update_data = {
            "status": BookingStatusChoices.cancelled.value,
        }
        response = self.client.put(
            self._get_booking_url(booking.external_id), update_data, format="json"
        )
        self.assertContains(
            response,
            status_code=400,
            text="Cannot cancel a booking. Use the cancel endpoint",
        )

    def test_cancel_booking_with_permission(self):
        """Users with proper permissions can cancel bookings via the cancel endpoint."""
        permissions = [
            UserSchedulePermissions.can_write_user_booking.name,
            UserSchedulePermissions.can_list_user_booking.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        booking = self.create_booking()
        tokens_allocated_before = booking.token_slot.allocated

        cancel_url = reverse(
            "appointments-cancel",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": booking.external_id,
            },
        )
        data = {"reason": BookingStatusChoices.cancelled.value}
        response = self.client.post(cancel_url, data, format="json")
        self.assertEqual(response.status_code, 200)

        booking.token_slot.refresh_from_db()
        tokens_allocated_after = booking.token_slot.allocated
        self.assertEqual(tokens_allocated_before - 1, tokens_allocated_after)

    def test_cancel_booking_without_permission(self):
        """Users without proper permissions cannot cancel bookings via the cancel endpoint."""
        permissions = [
            UserSchedulePermissions.can_list_user_booking.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        booking = self.create_booking()
        cancel_url = reverse(
            "appointments-cancel",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": booking.external_id,
            },
        )
        data = {"reason": BookingStatusChoices.cancelled.value}
        response = self.client.post(cancel_url, data, format="json")
        self.assertContains(
            response,
            status_code=403,
            text="You do not have permission to update bookings",
        )

    def test_cancel_cancelled_booking(self):
        """Users can cancel bookings to another cancelled status even if already cancelled. However, tokens allocated on slot won't be changed."""
        permissions = [
            UserSchedulePermissions.can_write_user_booking.name,
            UserSchedulePermissions.can_list_user_booking.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        booking = self.create_booking()
        cancel_url = reverse(
            "appointments-cancel",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": booking.external_id,
            },
        )

        data = {"reason": BookingStatusChoices.cancelled.value}
        response = self.client.post(cancel_url, data, format="json")
        self.assertEqual(response.status_code, 200)

        booking.token_slot.refresh_from_db()
        tokens_allocated_before = booking.token_slot.allocated

        data = {"reason": BookingStatusChoices.entered_in_error.value}
        response = self.client.post(cancel_url, data, format="json")
        self.assertEqual(response.status_code, 200)

        booking.token_slot.refresh_from_db()
        tokens_allocated_after = booking.token_slot.allocated
        self.assertEqual(tokens_allocated_before, tokens_allocated_after)

    def test_reschedule_booking_with_permission(self):
        """Users with proper permissions can reschedule bookings via the re-schedule endpoint."""
        permissions = [
            UserSchedulePermissions.can_write_user_booking.name,
            UserSchedulePermissions.can_list_user_booking.name,
            UserSchedulePermissions.can_create_appointment.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        new_slot = self.create_slot()
        booking = self.create_booking()
        reschedule_url = reverse(
            "appointments-reschedule",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": booking.external_id,
            },
        )
        data = {"new_slot": new_slot.external_id}
        response = self.client.post(reschedule_url, data, format="json")
        self.assertEqual(response.status_code, 200)

    def test_reschedule_booking_without_permission(self):
        """Users without proper permissions cannot reschedule bookings via the re-schedule endpoint."""
        permissions = [
            UserSchedulePermissions.can_write_user_booking.name,
            UserSchedulePermissions.can_list_user_booking.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        new_slot = self.create_slot()
        booking = self.create_booking()
        reschedule_url = reverse(
            "appointments-reschedule",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": booking.external_id,
            },
        )
        data = {"new_slot": new_slot.external_id}
        response = self.client.post(reschedule_url, data, format="json")
        self.assertContains(
            response,
            status_code=403,
            text="You do not have permission to create appointments",
        )

    def test_reschedule_booking_with_slot_in_past(self):
        """Users cannot reschedule bookings to slots that are in the past."""
        permissions = [
            UserSchedulePermissions.can_write_user_booking.name,
            UserSchedulePermissions.can_list_user_booking.name,
            UserSchedulePermissions.can_create_appointment.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        new_slot = self.create_slot(
            start_datetime=datetime.now(UTC) - timedelta(minutes=30),
            end_datetime=datetime.now(UTC) - timedelta(minutes=15),
        )
        booking = self.create_booking()
        reschedule_url = reverse(
            "appointments-reschedule",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": booking.external_id,
            },
        )
        data = {"new_slot": new_slot.external_id}
        response = self.client.post(reschedule_url, data, format="json")
        self.assertContains(
            response,
            status_code=400,
            text="Slot is already past",
        )

    def test_list_available_users(self):
        """Users can list available schedulable users."""
        available_users_url = reverse(
            "appointments-available-users",
            kwargs={"facility_external_id": self.facility.external_id},
        )
        response = self.client.get(available_users_url)
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data["users"]), 1)


@ignore_warnings(category=RuntimeWarning, message=r".*received a naive datetime.*")
class TestSlotViewSetAppointmentApi(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.patient = self.create_patient()
        self.resource = SchedulableUserResource.objects.create(
            user=self.user, facility=self.facility
        )
        self.schedule = Schedule.objects.create(
            resource=self.resource,
            name="Test Schedule",
            valid_from=datetime.now(UTC) - timedelta(days=30),
            valid_to=datetime.now(UTC) + timedelta(days=30),
        )
        self.availability = self.create_availability()
        self.slot = self.create_slot()
        self.client.force_authenticate(user=self.user)

    def _get_create_appointment_url(self, slot_id):
        """Helper to get the detail URL for a specific booking."""
        return reverse(
            "slot-create-appointment",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": slot_id,
            },
        )

    def create_appointment(self, **kwargs):
        data = {
            "token_slot": self.slot,
            "patient": self.patient,
            "booked_by": self.user,
            "status": BookingStatusChoices.booked.value,
        }
        data.update(kwargs)
        return TokenBooking.objects.create(**data)

    def create_slot(self, **kwargs):
        data = {
            "resource": self.resource,
            "availability": self.availability,
            "start_datetime": datetime.now(UTC) + timedelta(minutes=30),
            "end_datetime": datetime.now(UTC) + timedelta(minutes=60),
            "allocated": 0,
        }
        data.update(kwargs)
        return TokenSlot.objects.create(**data)

    def create_availability(self, **kwargs):
        return Availability.objects.create(
            schedule=self.schedule,
            name=kwargs.get("name", "Test Availability"),
            slot_type=kwargs.get("slot_type", SlotTypeOptions.appointment.value),
            slot_size_in_minutes=kwargs.get("slot_size_in_minutes", 30),
            tokens_per_slot=kwargs.get("tokens_per_slot", 1),
            create_tokens=kwargs.get("create_tokens", False),
            reason=kwargs.get("reason", "Regular schedule"),
            availability=kwargs.get(
                "availability",
                [
                    {
                        "day_of_week": 0,
                        "start_time": "09:00:00",
                        "end_time": "13:00:00",
                    },
                    {
                        "day_of_week": 1,
                        "start_time": "09:00:00",
                        "end_time": "13:00:00",
                    },
                    {
                        "day_of_week": 2,
                        "start_time": "09:00:00",
                        "end_time": "13:00:00",
                    },
                    {
                        "day_of_week": 3,
                        "start_time": "09:00:00",
                        "end_time": "13:00:00",
                    },
                    {
                        "day_of_week": 4,
                        "start_time": "09:00:00",
                        "end_time": "13:00:00",
                    },
                    {
                        "day_of_week": 5,
                        "start_time": "09:00:00",
                        "end_time": "13:00:00",
                    },
                    {
                        "day_of_week": 6,
                        "start_time": "09:00:00",
                        "end_time": "13:00:00",
                    },
                ],
            ),
        )

    def get_appointment_data(self, **kwargs):
        data = {
            "patient": self.patient.external_id,
            "reason_for_visit": "Testing",
        }
        data.update(kwargs)
        return data

    def test_create_appointment_with_permission(self):
        """Users with can_create_appointment permission can create appointments."""
        permissions = [UserSchedulePermissions.can_create_appointment.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        data = self.get_appointment_data()
        response = self.client.post(
            self._get_create_appointment_url(self.slot.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 200)

    def test_create_appointment_without_permission(self):
        """Users without can_create_appointment permission cannot create appointments."""
        data = self.get_appointment_data()
        response = self.client.post(
            self._get_create_appointment_url(self.slot.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_create_appointment_with_invalid_patient(self):
        """Users cannot create appointments for invalid patients."""
        permissions = [UserSchedulePermissions.can_create_appointment.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        data = self.get_appointment_data(patient="76aab2d8-93ef-4c9b-b344-b48167a082d0")
        response = self.client.post(
            self._get_create_appointment_url(self.slot.external_id), data, format="json"
        )
        self.assertContains(response, status_code=400, text="Patient not found")

    def test_create_appointment_with_slot_in_past(self):
        """Users cannot create appointments for slots that are in the past."""
        permissions = [UserSchedulePermissions.can_create_appointment.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        slot = self.create_slot(
            start_datetime=datetime.now(UTC) - timedelta(minutes=30),
            end_datetime=datetime.now(UTC) - timedelta(minutes=15),
        )
        data = self.get_appointment_data()
        response = self.client.post(
            self._get_create_appointment_url(slot.external_id), data, format="json"
        )
        self.assertContains(response, status_code=400, text="Slot is already past")

    def test_create_multiple_appointments_on_same_slot(self):
        """Users cannot create multiple appointments on the same slot for the same patient."""
        permissions = [UserSchedulePermissions.can_create_appointment.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        self.create_appointment()

        data = self.get_appointment_data()
        response = self.client.post(
            self._get_create_appointment_url(self.slot.external_id), data, format="json"
        )
        self.assertContains(
            response,
            status_code=400,
            text="Patient already has a booking for this slot",
        )

    def test_cancel_and_create_appointment_on_same_slot(self):
        """Users can create a new appointment on a slot after cancelling the previous one."""
        permissions = [UserSchedulePermissions.can_create_appointment.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        self.create_appointment(status=BookingStatusChoices.cancelled.value)

        data = self.get_appointment_data()
        response = self.client.post(
            self._get_create_appointment_url(self.slot.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 200)

    def test_over_booking_a_slot(self):
        """Users cannot create appointments on slots that are already fully booked."""
        permissions = [UserSchedulePermissions.can_create_appointment.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        availability = self.create_availability(tokens_per_slot=10)
        slot = self.create_slot(availability=availability, allocated=10)

        data = self.get_appointment_data()
        response = self.client.post(
            self._get_create_appointment_url(slot.external_id), data, format="json"
        )
        self.assertContains(response, status_code=400, text="Slot is already full")


@ignore_warnings(category=RuntimeWarning, message=r".*received a naive datetime.*")
class TestSlotViewSetSlotStatsApis(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.patient = self.create_patient()
        self.resource = SchedulableUserResource.objects.create(
            user=self.user,
            facility=self.facility,
        )
        self.schedule = Schedule.objects.create(
            resource=self.resource,
            name="Test Schedule",
            valid_from=datetime.now(UTC) - timedelta(days=30),
            valid_to=datetime.now(UTC) + timedelta(days=30),
        )
        self.availability = self.create_availability()
        self.client.force_authenticate(user=self.user)

    def create_availability(self, **kwargs):
        return Availability.objects.create(
            schedule=self.schedule,
            name=kwargs.get("name", "Test Availability"),
            slot_type=kwargs.get("slot_type", SlotTypeOptions.appointment.value),
            slot_size_in_minutes=kwargs.get("slot_size_in_minutes", 30),
            tokens_per_slot=kwargs.get("tokens_per_slot", 1),
            create_tokens=kwargs.get("create_tokens", False),
            reason=kwargs.get("reason", "Regular schedule"),
            availability=kwargs.get(
                "availability",
                [
                    {
                        "day_of_week": 0,
                        "start_time": "09:00:00",
                        "end_time": "13:00:00",
                    },
                    {
                        "day_of_week": 1,
                        "start_time": "09:00:00",
                        "end_time": "13:00:00",
                    },
                    {
                        "day_of_week": 2,
                        "start_time": "09:00:00",
                        "end_time": "13:00:00",
                    },
                    {
                        "day_of_week": 3,
                        "start_time": "09:00:00",
                        "end_time": "13:00:00",
                    },
                    {
                        "day_of_week": 4,
                        "start_time": "09:00:00",
                        "end_time": "13:00:00",
                    },
                    {
                        "day_of_week": 5,
                        "start_time": "09:00:00",
                        "end_time": "13:00:00",
                    },
                    {
                        "day_of_week": 6,
                        "start_time": "09:00:00",
                        "end_time": "13:00:00",
                    },
                ],
            ),
        )

    def _get_slot_for_day_url(self, facility_id=None):
        return reverse(
            "slot-get-slots-for-day",
            kwargs={
                "facility_external_id": facility_id or self.facility.external_id,
            },
        )

    def _get_availability_stats_url(self, facility_id=None):
        return reverse(
            "slot-availability-stats",
            kwargs={"facility_external_id": facility_id or self.facility.external_id},
        )

    def test_get_slots_for_day(self):
        """Users can get available slots for a specific day."""
        data = {
            "user": self.user.external_id,
            "day": datetime.now(UTC).strftime("%Y-%m-%d"),
        }
        response = self.client.post(self._get_slot_for_day_url(), data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 8)

    def test_hit_on_get_slots_for_day_does_not_cause_duplicate_slots(self):
        """Multiple requests to get slots for a day should not create duplicate slots."""
        data = {
            "user": self.user.external_id,
            "day": datetime.now(UTC).strftime("%Y-%m-%d"),
        }
        url = self._get_slot_for_day_url()

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 8)

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 8)

    def test_get_slots_for_day_for_non_schedulable_user(self):
        """Cannot get slots for users that are not schedulable."""
        user = self.create_user()
        facility = self.create_facility(user=user)
        data = {
            "user": user.external_id,
            "day": datetime.now(UTC).strftime("%Y-%m-%d"),
        }
        response = self.client.post(
            self._get_slot_for_day_url(facility.external_id), data, format="json"
        )
        self.assertContains(
            response, status_code=400, text="Resource is not schedulable"
        )

    def test_get_slots_for_day_with_full_day_exception(self):
        """No slots should be available for days with full day exceptions."""
        AvailabilityException.objects.create(
            resource=self.resource,
            name="Test Exception",
            valid_from=datetime.now(UTC) - timedelta(days=1),
            valid_to=datetime.now(UTC) + timedelta(days=1),
            start_time="00:00:00",
            end_time="23:59:59",
        )
        data = {
            "user": self.user.external_id,
            "day": datetime.now(UTC).strftime("%Y-%m-%d"),
        }
        response = self.client.post(self._get_slot_for_day_url(), data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 0)

    def test_get_slots_for_day_with_exception_left_overlap(self):
        """Fewer slots should be available when there is an exception overlapping the start of the day."""
        AvailabilityException.objects.create(
            resource=self.resource,
            name="Test Exception",
            valid_from=datetime.now(UTC) - timedelta(days=1),
            valid_to=datetime.now(UTC) + timedelta(days=1),
            start_time="00:00:00",
            end_time="12:00:00",
        )
        data = {
            "user": self.user.external_id,
            "day": datetime.now(UTC).strftime("%Y-%m-%d"),
        }
        response = self.client.post(self._get_slot_for_day_url(), data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)

    def test_get_slots_for_day_with_exception_right_overlap(self):
        """Fewer slots should be available when there is an exception overlapping the end of the day."""
        AvailabilityException.objects.create(
            resource=self.resource,
            name="Test Exception",
            valid_from=datetime.now(UTC) - timedelta(days=1),
            valid_to=datetime.now(UTC) + timedelta(days=1),
            start_time="10:00:00",
            end_time="23:59:59",
        )
        data = {
            "user": self.user.external_id,
            "day": datetime.now(UTC).strftime("%Y-%m-%d"),
        }
        response = self.client.post(self._get_slot_for_day_url(), data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)

    def test_get_slots_for_day_with_exception_overlap_in_between(self):
        """Fewer slots should be available when there is an exception overlapping the middle of the day."""
        AvailabilityException.objects.create(
            resource=self.resource,
            name="Test Exception",
            valid_from=datetime.now(UTC) - timedelta(days=1),
            valid_to=datetime.now(UTC) + timedelta(days=1),
            start_time="10:00:00",
            end_time="12:00:00",
        )
        data = {
            "user": self.user.external_id,
            "day": datetime.now(UTC).strftime("%Y-%m-%d"),
        }
        response = self.client.post(self._get_slot_for_day_url(), data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 4)

    def test_availability_stats(self):
        """Users can get availability statistics for a date range."""
        data = {
            "user": self.user.external_id,
            "from_date": datetime.now(UTC).strftime("%Y-%m-%d"),
            "to_date": (datetime.now(UTC) + timedelta(days=10)).strftime("%Y-%m-%d"),
        }
        response = self.client.post(
            self._get_availability_stats_url(), data, format="json"
        )
        self.assertEqual(response.status_code, 200)

    def test_availability_stats_partially_outside_schedule_validity(self):
        """Users can get availability statistics for date ranges partially outside schedule validity."""
        data = {
            "user": self.user.external_id,
            "from_date": (datetime.now(UTC) + timedelta(days=25)).strftime("%Y-%m-%d"),
            "to_date": (datetime.now(UTC) + timedelta(days=35)).strftime("%Y-%m-%d"),
        }
        response = self.client.post(
            self._get_availability_stats_url(), data, format="json"
        )
        self.assertEqual(response.status_code, 200)

    def test_availability_stats_invalid_period(self):
        """Users cannot get availability statistics when from_date is after to_date."""
        data = {
            "user": self.user.external_id,
            "from_date": (datetime.now(UTC) + timedelta(days=10)).strftime("%Y-%m-%d"),
            "to_date": (datetime.now(UTC) + timedelta(days=1)).strftime("%Y-%m-%d"),
        }
        response = self.client.post(
            self._get_availability_stats_url(), data, format="json"
        )
        self.assertContains(
            response, status_code=400, text="From Date cannot be after To Date"
        )

    def test_availability_stats_exceed_period(self):
        """Users cannot get availability statistics for periods longer than the maximum allowed days."""
        data = {
            "user": self.user.external_id,
            "from_date": datetime.now(UTC).strftime("%Y-%m-%d"),
            "to_date": (datetime.now(UTC) + timedelta(days=40)).strftime("%Y-%m-%d"),
        }
        response = self.client.post(
            self._get_availability_stats_url(), data, format="json"
        )
        self.assertContains(
            response, status_code=400, text="Period cannot be be greater than 32 days"
        )

    def test_availability_stats_for_invalid_user(self):
        """Users cannot get availability statistics for invalid users."""
        data = {
            "user": "98c763ba-5bbb-44b9-ac03-56414fbb3021",
            "from_date": datetime.now(UTC).strftime("%Y-%m-%d"),
            "to_date": (datetime.now(UTC) + timedelta(days=10)).strftime("%Y-%m-%d"),
        }
        response = self.client.post(
            self._get_availability_stats_url(), data, format="json"
        )
        self.assertContains(response, status_code=400, text="User does not exist")

    def test_availability_stats_for_non_schedulable_user(self):
        """Users cannot get availability statistics for non-schedulable users."""
        non_schedulable_user = self.create_user()
        data = {
            "user": non_schedulable_user.external_id,
            "from_date": datetime.now(UTC).strftime("%Y-%m-%d"),
            "to_date": (datetime.now(UTC) + timedelta(days=10)).strftime("%Y-%m-%d"),
        }
        response = self.client.post(
            self._get_availability_stats_url(), data, format="json"
        )
        self.assertContains(
            response, status_code=400, text="Resource is not schedulable"
        )

    def test_availability_heatmap_slots_same_as_get_slots_for_day_without_exceptions(
        self,
    ):
        """Availability heatmap slot counts should match individual day slot counts when there are no exceptions."""
        data = {
            "user": self.user.external_id,
            "from_date": datetime.now(UTC).strftime("%Y-%m-%d"),
            "to_date": (datetime.now(UTC) + timedelta(days=7)).strftime("%Y-%m-%d"),
        }
        response = self.client.post(
            self._get_availability_stats_url(), data, format="json"
        )
        self.assertEqual(response.status_code, 200)

        for day, slot_stats in response.data.items():
            data = {"user": self.user.external_id, "day": day}
            response = self.client.post(
                self._get_slot_for_day_url(), data, format="json"
            )
            self.assertEqual(response.status_code, 200)
            booked_slots_for_day = sum(x["allocated"] for x in response.data["results"])
            total_slots_for_day = sum(
                x["availability"]["tokens_per_slot"] for x in response.data["results"]
            )
            self.assertEqual(slot_stats["booked_slots"], booked_slots_for_day)
            self.assertEqual(slot_stats["total_slots"], total_slots_for_day)

    def test_availability_heatmap_slots_same_as_get_slots_for_day_with_exceptions(self):
        """Availability heatmap slot counts should match individual day slot counts even with exceptions."""
        AvailabilityException.objects.create(
            resource=self.resource,
            name="Test Exception",
            valid_from=datetime.now(UTC),
            valid_to=datetime.now(UTC) + timedelta(days=1),
            start_time="00:00:00",
            end_time="23:59:59",
        )
        AvailabilityException.objects.create(
            resource=self.resource,
            name="Test Exception",
            valid_from=datetime.now(UTC) + timedelta(days=2),
            valid_to=datetime.now(UTC) + timedelta(days=3),
            start_time="12:00:00",
            end_time="14:00:00",
        )
        data = {
            "user": self.user.external_id,
            "from_date": datetime.now(UTC).strftime("%Y-%m-%d"),
            "to_date": (datetime.now(UTC) + timedelta(days=7)).strftime("%Y-%m-%d"),
        }
        availability_stats_url = reverse(
            "slot-availability-stats",
            kwargs={"facility_external_id": self.facility.external_id},
        )
        response = self.client.post(availability_stats_url, data, format="json")
        self.assertEqual(response.status_code, 200)

        slots_for_day_url = reverse(
            "slot-get-slots-for-day",
            kwargs={"facility_external_id": self.facility.external_id},
        )
        for day, slot_stats in response.data.items():
            data = {"user": self.user.external_id, "day": day}
            response = self.client.post(slots_for_day_url, data, format="json")
            self.assertEqual(response.status_code, 200)
            booked_slots_for_day = sum(x["allocated"] for x in response.data["results"])
            total_slots_for_day = sum(
                x["availability"]["tokens_per_slot"] for x in response.data["results"]
            )
            self.assertEqual(slot_stats["booked_slots"], booked_slots_for_day)
            self.assertEqual(slot_stats["total_slots"], total_slots_for_day)


@ignore_warnings(category=RuntimeWarning, message=r".*received a naive datetime.*")
class TestOtpSlotViewSet(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.patient = self.create_patient(phone_number="+917777777777")
        self.resource = SchedulableUserResource.objects.create(
            user=self.user, facility=self.facility
        )
        self.schedule = Schedule.objects.create(
            resource=self.resource,
            name="Test Schedule",
            valid_from=datetime.now(UTC) - timedelta(days=30),
            valid_to=datetime.now(UTC) + timedelta(days=30),
        )
        self.availability = self.create_availability()
        self.slot = self.create_slot()
        self.client.force_authenticate(user=self.get_patient_otp_object())

    def get_patient_otp_object(self):
        obj = PatientOtpObject()
        obj.phone_number = self.patient.phone_number
        return obj

    def create_appointment(self, **kwargs):
        data = {
            "token_slot": self.slot,
            "patient": self.patient,
            "booked_by": self.user,
            "status": BookingStatusChoices.booked.value,
        }
        data.update(kwargs)
        return TokenBooking.objects.create(**data)

    def create_slot(self, **kwargs):
        data = {
            "resource": self.resource,
            "availability": self.availability,
            "start_datetime": datetime.now(UTC) + timedelta(minutes=30),
            "end_datetime": datetime.now(UTC) + timedelta(minutes=60),
            "allocated": 0,
        }
        data.update(kwargs)
        return TokenSlot.objects.create(**data)

    def create_availability(self, **kwargs):
        return Availability.objects.create(
            schedule=self.schedule,
            name=kwargs.get("name", "Test Availability"),
            slot_type=kwargs.get("slot_type", SlotTypeOptions.appointment.value),
            slot_size_in_minutes=kwargs.get("slot_size_in_minutes", 30),
            tokens_per_slot=kwargs.get("tokens_per_slot", 1),
            create_tokens=kwargs.get("create_tokens", False),
            reason=kwargs.get("reason", "Regular schedule"),
            availability=kwargs.get(
                "availability",
                [
                    {
                        "day_of_week": 0,
                        "start_time": "09:00:00",
                        "end_time": "13:00:00",
                    },
                    {
                        "day_of_week": 1,
                        "start_time": "09:00:00",
                        "end_time": "13:00:00",
                    },
                    {
                        "day_of_week": 2,
                        "start_time": "09:00:00",
                        "end_time": "13:00:00",
                    },
                    {
                        "day_of_week": 3,
                        "start_time": "09:00:00",
                        "end_time": "13:00:00",
                    },
                    {
                        "day_of_week": 4,
                        "start_time": "09:00:00",
                        "end_time": "13:00:00",
                    },
                    {
                        "day_of_week": 5,
                        "start_time": "09:00:00",
                        "end_time": "13:00:00",
                    },
                    {
                        "day_of_week": 6,
                        "start_time": "09:00:00",
                        "end_time": "13:00:00",
                    },
                ],
            ),
        )

    def test_get_slots_for_day(self):
        """OTP authenticated users can get available slots for a specific day."""
        url = reverse("otp-slots-get-slots-for-day")
        data = {
            "user": self.user.external_id,
            "day": datetime.now(UTC).strftime("%Y-%m-%d"),
            "facility": self.facility.external_id,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)

    def test_get_slots_for_day_without_facility(self):
        """OTP authenticated users cannot get slots without specifying a facility."""
        url = reverse("otp-slots-get-slots-for-day")
        data = {
            "user": self.user.external_id,
            "day": datetime.now(UTC).strftime("%Y-%m-%d"),
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 400)

    def test_create_appointment(self):
        """OTP authenticated users can create appointments."""
        data = {
            "patient": self.patient.external_id,
            "reason_for_visit": "Test Reason",
        }
        url = reverse(
            "otp-slots-create-appointment",
            kwargs={"external_id": self.slot.external_id},
        )
        response = self.client.post(url, data, format="json")
        self.assertContains(response, BookingStatusChoices.booked.value)

    def test_create_appointment_of_another_patient(self):
        """OTP authenticated users cannot create appointments for other patients."""
        other_patient = self.create_patient(phone_number="+917777777778")
        data = {
            "patient": other_patient.external_id,
            "reason_for_visit": "Test Reason",
        }
        url = reverse(
            "otp-slots-create-appointment",
            kwargs={"external_id": self.slot.external_id},
        )
        response = self.client.post(url, data, format="json")
        self.assertContains(response, "Patient not allowed", status_code=400)

    def test_cancel_appointment(self):
        """OTP authenticated users can cancel their own appointments."""
        booking = self.create_appointment()
        url = reverse("otp-slots-cancel-appointment")
        data = {
            "patient": booking.patient.external_id,
            "appointment": booking.external_id,
        }
        response = self.client.post(url, data, format="json")
        self.assertContains(response, BookingStatusChoices.cancelled.value)

    def test_cancel_appointment_of_another_patient(self):
        """OTP authenticated users cannot cancel appointments of other patients."""
        other_patient = self.create_patient(phone_number="+917777777778")
        booking = self.create_appointment(patient=other_patient)
        url = reverse("otp-slots-cancel-appointment")
        data = {
            "patient": booking.patient.external_id,
            "appointment": booking.external_id,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 404)

    def test_get_appointments(self):
        """OTP authenticated users can get their own appointments."""
        booking = self.create_appointment()
        url = reverse("otp-slots-get-appointments")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], booking.external_id)

    def test_get_appointments_of_another_patient(self):
        """OTP authenticated users cannot get appointments of other patients."""
        other_patient = self.create_patient(phone_number="+917777777778")
        self.create_appointment(patient=other_patient)
        url = reverse("otp-slots-get-appointments")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 0)
