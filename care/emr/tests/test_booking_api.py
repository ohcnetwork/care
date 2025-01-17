from http.client import responses

from care.emr.models import (
    SchedulableUserResource,
    Schedule,
    Availability,
    TokenSlot,
    TokenBooking,
    AvailabilityException,
)
from care.emr.resources.scheduling.schedule.spec import SlotTypeOptions
from care.emr.resources.scheduling.slot.spec import BookingStatusChoices
from care.security.permissions.user_schedule import UserSchedulePermissions
from care.utils.tests.base import CareAPITestBase
from django.urls import reverse
from datetime import datetime, timedelta


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
            valid_from=datetime.now() - timedelta(days=30),
            valid_to=datetime.now() + timedelta(days=30),
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
        return TokenBooking.objects.create(**data)

    def create_slot(self, **kwargs):
        data = {
            "resource": self.resource,
            "availability": self.availability,
            "start_datetime": datetime.now() + timedelta(minutes=30),
            "end_datetime": datetime.now() + timedelta(minutes=60),
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
        """Users can cancel bookings via the cancel endpoint."""
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

    def test_cancel_booking_without_permission(self):
        """Users cannot cancel bookings via the cancel endpoint."""
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

    def test_reschedule_booking_with_permission(self):
        """Users can reschedule bookings via the re-schedule endpoint."""
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
        """Users cannot reschedule bookings via the re-schedule endpoint."""
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
        """Users cannot reschedule bookings via the re-schedule endpoint."""
        permissions = [
            UserSchedulePermissions.can_write_user_booking.name,
            UserSchedulePermissions.can_list_user_booking.name,
            UserSchedulePermissions.can_create_appointment.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        new_slot = self.create_slot(
            start_datetime=datetime.now() - timedelta(minutes=30),
            end_datetime=datetime.now() - timedelta(minutes=15),
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
        available_users_url = reverse(
            "appointments-available-users",
            kwargs={"facility_external_id": self.facility.external_id},
        )
        response = self.client.get(available_users_url)
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data["users"]), 1)


class TestSlotViewSet(CareAPITestBase):
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
            valid_from=datetime.now() - timedelta(days=30),
            valid_to=datetime.now() + timedelta(days=30),
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
            "start_datetime": datetime.now() + timedelta(minutes=30),
            "end_datetime": datetime.now() + timedelta(minutes=60),
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

    def test_create_appointment_with_slot_in_past(self):
        """Users cannot create appointments on a past slot."""
        permissions = [UserSchedulePermissions.can_create_appointment.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        slot = self.create_slot(
            start_datetime=datetime.now() - timedelta(minutes=30),
            end_datetime=datetime.now() - timedelta(minutes=15),
        )
        data = self.get_appointment_data()
        response = self.client.post(
            self._get_create_appointment_url(slot.external_id), data, format="json"
        )
        self.assertContains(response, status_code=400, text="Slot is already past")

    def test_create_multiple_appointments_on_same_slot(self):
        """Users cannot create multiple appointments on the same slot (as long as previous ones are cancelled)"""
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
        """Users can create an appointment on the same slot if the previous one is cancelled"""
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
        """Users cannot create an appointment on a slot if it is already fully booked"""
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

    def test_get_slots_for_day(self):
        """Get slots for a specific day."""
        data = {
            "user": self.user.external_id,
            "day": datetime.now().strftime("%Y-%m-%d"),
        }
        url = reverse(
            "slot-get-slots-for-day",
            kwargs={"facility_external_id": self.facility.external_id},
        )
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)

    def test_get_slots_for_day_for_non_schedulable_user(self):
        """Cannot get slots for non-schedulable user."""
        user = self.create_user()
        facility = self.create_facility(user=user)
        data = {
            "user": user.external_id,
            "day": datetime.now().strftime("%Y-%m-%d"),
        }
        url = reverse(
            "slot-get-slots-for-day",
            kwargs={"facility_external_id": facility.external_id},
        )
        response = self.client.post(url, data, format="json")
        self.assertContains(
            response, status_code=400, text="Resource is not schedulable"
        )

    def test_get_slots_for_day_with_exception(self):
        """Get no slots for day with whole day exception"""

        # we don't want the slot that was created in setUp; create availability exception would've done this for us anyways.
        self.slot.delete()

        AvailabilityException.objects.create(
            resource=self.resource,
            name="Test Exception",
            valid_from=datetime.now() - timedelta(days=1),
            valid_to=datetime.now() + timedelta(days=1),
            start_time="00:00:00",
            end_time="23:59:59",
        )
        data = {
            "user": self.user.external_id,
            "day": datetime.now().strftime("%Y-%m-%d"),
        }
        url = reverse(
            "slot-get-slots-for-day",
            kwargs={"facility_external_id": self.facility.external_id},
        )
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 0)
