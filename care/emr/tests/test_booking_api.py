from care.emr.models import (
    SchedulableUserResource,
    Schedule,
    Availability,
    TokenSlot,
    TokenBooking,
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
        print(response.data)
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
    pass
