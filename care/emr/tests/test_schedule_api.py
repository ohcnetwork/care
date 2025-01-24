from datetime import UTC, datetime, timedelta

from django.test.utils import ignore_warnings
from django.urls import reverse
from rest_framework import status

from care.emr.models import (
    Availability,
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


@ignore_warnings(category=RuntimeWarning, message=r".*received a naive datetime.*")
class TestScheduleViewSet(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.resource = SchedulableUserResource.objects.create(
            user=self.user,
            facility=self.facility,
        )
        self.patient = self.create_patient()
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
            "schedule-list", kwargs={"facility_external_id": self.facility.external_id}
        )

    def _get_schedule_url(self, schedule_id):
        """Helper to get the detail URL for a specific schedule."""
        return reverse(
            "schedule-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": schedule_id,
            },
        )

    def create_schedule(self, **kwargs):
        from care.emr.models import Schedule

        schedule = Schedule.objects.create(
            resource=self.resource,
            name=kwargs.get("name", "Test Schedule"),
            valid_from=kwargs.get("valid_from", datetime.now(UTC)),
            valid_to=kwargs.get("valid_to", datetime.now(UTC) + timedelta(days=30)),
        )
        for availability in kwargs.get("availabilities", []):
            schedule.availabilities.create(**availability)
        return schedule

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

    def generate_schedule_data(self, **kwargs):
        """Helper to generate valid schedule data."""
        valid_from = datetime.now(UTC)
        valid_to = valid_from + timedelta(days=30)

        return {
            "user": str(self.user.external_id),
            "name": "Test Schedule",
            "valid_from": valid_from.isoformat(),
            "valid_to": valid_to.isoformat(),
            "availabilities": [
                {
                    "name": "Morning Slot",
                    "slot_type": SlotTypeOptions.appointment.value,
                    "slot_size_in_minutes": 30,
                    "tokens_per_slot": 1,
                    "create_tokens": True,
                    "reason": "Regular schedule",
                    "availability": [
                        {
                            "day_of_week": 1,
                            "start_time": "09:00:00",
                            "end_time": "13:00:00",
                        }
                    ],
                }
            ],
            **kwargs,
        }

    # LIST TESTS
    def test_list_schedule_with_permissions(self):
        """Users with can_list_user_schedule permission can list schedules."""
        permissions = [UserSchedulePermissions.can_list_user_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_schedule_without_permissions(self):
        """Users without can_list_user_schedule permission cannot list schedules."""
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_schedule_with_permissions(self):
        """Users with can_write_user_schedule permission can create schedules."""
        permissions = [UserSchedulePermissions.can_write_user_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        schedule_data = self.generate_schedule_data()
        response = self.client.post(self.base_url, schedule_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], schedule_data["name"])

    def test_create_schedule_without_permissions(self):
        """Users without can_write_user_schedule permission cannot create schedules."""
        schedule_data = self.generate_schedule_data()
        response = self.client.post(self.base_url, schedule_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_schedule_with_invalid_dates(self):
        """Schedule creation fails when valid_from is after valid_to."""
        permissions = [UserSchedulePermissions.can_write_user_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        valid_from = datetime.now(UTC)
        valid_to = valid_from - timedelta(days=1)  # Invalid: end before start

        schedule_data = self.generate_schedule_data(
            valid_from=valid_from.isoformat(), valid_to=valid_to.isoformat()
        )
        response = self.client.post(self.base_url, schedule_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertContains(
            response, "Valid from cannot be greater than valid to", status_code=400
        )

    def test_create_schedule_with_user_not_part_of_facility(self):
        """Users cannot write schedules for user not belonging to the facility."""
        permissions = [UserSchedulePermissions.can_write_user_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        user = self.create_user()
        schedule_data = self.generate_schedule_data(user=user.external_id)
        response = self.client.post(self.base_url, schedule_data, format="json")
        self.assertContains(
            response, "Schedule User is not part of the facility", status_code=400
        )

    def test_update_schedule_with_permissions(self):
        """Users with can_write_user_schedule permission can update schedules."""
        permissions = [
            UserSchedulePermissions.can_write_user_schedule.name,
            UserSchedulePermissions.can_list_user_schedule.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        # First create a schedule
        schedule = self.create_schedule()

        # Then update it
        updated_data = {
            "name": "Updated Schedule Name",
            "valid_from": schedule.valid_from,
            "valid_to": schedule.valid_to,
        }
        update_url = self._get_schedule_url(schedule.external_id)
        response = self.client.put(update_url, updated_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Updated Schedule Name")

    def test_update_schedule_without_permissions(self):
        """Users without can_write_user_schedule permission cannot update schedules."""
        # First create a schedule with permissions
        permissions = [
            UserSchedulePermissions.can_list_user_schedule.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        schedule = self.create_schedule()

        updated_data = {
            "name": "Updated Schedule Name",
            "valid_from": schedule.valid_from,
            "valid_to": schedule.valid_to,
        }
        update_url = self._get_schedule_url(schedule.external_id)
        response = self.client.put(update_url, updated_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # DELETE TESTS
    def test_delete_schedule_with_permissions(self):
        """Users with can_write_user_schedule permission can delete schedules."""
        permissions = [
            UserSchedulePermissions.can_write_user_schedule.name,
            UserSchedulePermissions.can_list_user_schedule.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        schedule = self.create_schedule()
        delete_url = self._get_schedule_url(schedule.external_id)
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_schedule_without_permissions(self):
        """Users without can_write_user_schedule permission cannot delete schedules."""
        # First create a schedule with permissions
        permissions = [
            UserSchedulePermissions.can_list_user_schedule.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        schedule = self.create_schedule()
        delete_url = self._get_schedule_url(schedule.external_id)
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_schedule_validity_with_booking_within_new_validity(self):
        """Test that schedule validity can be updated when bookings fall within the new validity period."""
        permissions = [
            UserSchedulePermissions.can_write_user_schedule.name,
            UserSchedulePermissions.can_list_user_schedule.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        self.create_booking()
        updated_data = {
            "name": "Updated Schedule Name",
            "valid_from": self.schedule.valid_from,
            "valid_to": self.schedule.valid_to - timedelta(days=1),
        }
        update_url = self._get_schedule_url(self.schedule.external_id)
        response = self.client.put(update_url, updated_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_schedule_validity_with_booking_outside_new_validity(self):
        """Test that schedule validity cannot be updated when bookings fall outside the new validity period."""
        permissions = [
            UserSchedulePermissions.can_write_user_schedule.name,
            UserSchedulePermissions.can_list_user_schedule.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        self.create_booking(
            token_slot=self.create_slot(
                start_datetime=datetime.now(UTC) + timedelta(days=4),
                end_datetime=datetime.now(UTC) + timedelta(days=5),
            )
        )
        updated_data = {
            "name": "Updated Schedule Name",
            "valid_from": self.schedule.valid_from,
            "valid_to": self.schedule.valid_from + timedelta(days=1),
        }
        update_url = self._get_schedule_url(self.schedule.external_id)
        response = self.client.put(update_url, updated_data, format="json")
        self.assertContains(
            response,
            status_code=400,
            text="Cannot modify schedule validity as it would exclude some allocated slots. Old range has 1 allocated slots while new range has 0 allocated slots.",
        )

    def test_delete_schedule_with_future_bookings(self):
        """Users cannot delete schedules with bookings present in the future."""
        permissions = [
            UserSchedulePermissions.can_write_user_schedule.name,
            UserSchedulePermissions.can_list_user_schedule.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        self.create_booking(
            token_slot=self.create_slot(
                start_datetime=datetime.now(UTC) + timedelta(days=4),
                end_datetime=datetime.now(UTC) + timedelta(days=5),
            )
        )
        delete_url = self._get_schedule_url(self.schedule.external_id)
        response = self.client.delete(delete_url)
        self.assertContains(
            response,
            status_code=400,
            text="Cannot delete schedule as there are future bookings associated with it",
        )

    def test_delete_schedule_with_future_cancelled_bookings(self):
        """Users cannot delete schedules with bookings present in the future."""
        permissions = [
            UserSchedulePermissions.can_write_user_schedule.name,
            UserSchedulePermissions.can_list_user_schedule.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        self.create_booking(
            token_slot=self.create_slot(
                start_datetime=datetime.now(UTC) + timedelta(days=4),
                end_datetime=datetime.now(UTC) + timedelta(days=5),
            ),
            status=BookingStatusChoices.cancelled.value,
        )
        delete_url = self._get_schedule_url(self.schedule.external_id)
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


@ignore_warnings(category=RuntimeWarning, message=r".*received a naive datetime.*")
class TestAvailabilityExceptionsViewSet(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.resource = SchedulableUserResource.objects.create(
            user=self.user,
            facility=self.facility,
        )
        self.client.force_authenticate(user=self.user)

        self.base_url = reverse(
            "schedule-exceptions-list",
            kwargs={"facility_external_id": self.facility.external_id},
        )

    def _get_exception_url(self, exception_id):
        """Helper to get the detail URL for a specific availability exception."""
        return reverse(
            "schedule-exceptions-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": exception_id,
            },
        )

    def create_exception(self, **kwargs):
        from care.emr.models import AvailabilityException

        valid_from = datetime.now(UTC).date()
        valid_to = (datetime.now(UTC) + timedelta(days=1)).date()
        return AvailabilityException.objects.create(
            resource=self.resource,
            valid_from=valid_from,
            valid_to=valid_to,
            start_time=kwargs.get("start_time", "09:00:00"),
            end_time=kwargs.get("end_time", "17:00:00"),
            reason=kwargs.get("reason", "Out of office"),
        )

    def generate_exception_data(self, **kwargs):
        """Helper to generate valid availability exception data."""
        valid_from = datetime.now(UTC).date()
        valid_to = (datetime.now(UTC) + timedelta(days=1)).date()

        return {
            "user": str(self.user.external_id),
            "reason": "Out of office",
            "valid_from": valid_from.isoformat(),
            "valid_to": valid_to.isoformat(),
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            **kwargs,
        }

    def test_list_exceptions_with_permissions(self):
        """Users with can_list_user_schedule permission can list exceptions."""
        permissions = [UserSchedulePermissions.can_list_user_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_exceptions_without_permissions(self):
        """Users without can_list_user_schedule permission cannot list exceptions."""
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_exception_with_permissions(self):
        """Users with can_write_user_schedule permission can create exceptions."""
        permissions = [UserSchedulePermissions.can_write_user_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        exception_data = self.generate_exception_data()
        response = self.client.post(self.base_url, exception_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["reason"], exception_data["reason"])

    def test_create_exception_without_permissions(self):
        """Users without can_write_user_schedule permission cannot create exceptions."""
        exception_data = self.generate_exception_data()
        response = self.client.post(self.base_url, exception_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_exception_with_invalid_user_resource(self):
        """Users with can_write_user_schedule permission can create exceptions."""
        permissions = [UserSchedulePermissions.can_write_user_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        # Resource doesn't exist
        self.resource.delete()

        exception_data = self.generate_exception_data()
        response = self.client.post(self.base_url, exception_data, format="json")
        self.assertContains(response, "Object does not exist", status_code=400)

    def test_update_exception_with_permissions(self):
        """Users with can_write_user_schedule permission can update exceptions."""
        permissions = [
            UserSchedulePermissions.can_write_user_schedule.name,
            UserSchedulePermissions.can_list_user_schedule.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        # First create an exception
        exception = self.create_exception()

        # Then update it
        updated_data = {
            "user": str(self.user.external_id),
            "reason": "Updated reason",
            "valid_from": exception.valid_from,
            "valid_to": exception.valid_to,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
        }
        update_url = self._get_exception_url(exception.external_id)
        response = self.client.put(update_url, updated_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["reason"], "Updated reason")

    def test_update_exception_without_permissions(self):
        """Users without can_write_user_schedule permission cannot update exceptions."""
        permissions = [UserSchedulePermissions.can_list_user_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        # First create an exception
        exception = self.create_exception()

        updated_data = {
            "user": str(self.user.external_id),
            "reason": "Updated reason",
            "valid_from": exception.valid_from,
            "valid_to": exception.valid_to,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
        }
        update_url = self._get_exception_url(exception.external_id)
        response = self.client.put(update_url, updated_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_exception_with_permissions(self):
        """Users with can_write_user_schedule permission can delete exceptions."""
        permissions = [
            UserSchedulePermissions.can_write_user_schedule.name,
            UserSchedulePermissions.can_list_user_schedule.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        # First create an exception
        exception = self.create_exception()

        # Then delete it
        delete_url = self._get_exception_url(exception.external_id)
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_exception_without_permissions(self):
        """Users without can_write_user_schedule permission cannot delete exceptions."""
        # First create an exception with permissions
        permissions = [UserSchedulePermissions.can_write_user_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        exception = self.create_exception()

        delete_url = self._get_exception_url(exception.external_id)
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_exception_with_bookings(self):
        """Test that creating an exception fails when there are conflicting bookings."""
        permissions = [UserSchedulePermissions.can_write_user_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        # Create a schedule
        schedule = Schedule.objects.create(
            resource=self.resource,
            name="Test Schedule",
            valid_from=datetime.now(UTC) - timedelta(days=30),
            valid_to=datetime.now(UTC) + timedelta(days=30),
        )

        # Create an availability
        availability = Availability.objects.create(
            schedule=schedule,
            name="Test Availability",
            slot_type=SlotTypeOptions.appointment.value,
            slot_size_in_minutes=30,
            tokens_per_slot=1,
            create_tokens=False,
            reason="Regular schedule",
            availability=[
                {
                    "day_of_week": datetime.now(UTC).weekday(),
                    "start_time": "09:00:00",
                    "end_time": "17:00:00",
                }
            ],
        )

        # Create a slot for today
        slot_start = datetime.now(UTC).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        slot = TokenSlot.objects.create(
            resource=self.resource,
            availability=availability,
            start_datetime=slot_start,
            end_datetime=slot_start + timedelta(minutes=30),
            allocated=1,
        )

        # Create a booking for the slot
        patient = self.create_patient()
        TokenBooking.objects.create(
            token_slot=slot,
            patient=patient,
            booked_by=self.user,
            status=BookingStatusChoices.booked.value,
        )

        # Try to create an exception that overlaps with the booking
        exception_data = self.generate_exception_data(
            valid_from=slot_start.date().isoformat(),
            valid_to=slot_start.date().isoformat(),
            start_time="09:00:00",
            end_time="17:00:00",
        )

        response = self.client.post(self.base_url, exception_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertContains(
            response,
            "There are bookings during this exception",
            status_code=400,
        )


@ignore_warnings(category=RuntimeWarning, message=r".*received a naive datetime.*")
class TestAvailabilityViewSet(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.client.force_authenticate(user=self.user)
        self.resource = SchedulableUserResource.objects.create(
            user=self.user, facility=self.facility
        )
        self.resource = SchedulableUserResource.objects.create(
            user=self.user,
            facility=self.facility,
        )
        self.schedule = self.create_schedule()

        self.base_url = reverse(
            "schedule-availability-list",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "schedule_external_id": self.schedule.external_id,
            },
        )

    def _get_availability_url(self, availability_id):
        """Helper to get the detail url for a specific availability."""
        return reverse(
            "schedule-availability-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "schedule_external_id": self.schedule.external_id,
                "external_id": availability_id,
            },
        )

    def create_schedule(self, **kwargs):
        from care.emr.models import Schedule

        schedule = Schedule.objects.create(
            resource=self.resource,
            name=kwargs.get("name", "Test Schedule"),
            valid_from=kwargs.get("valid_from", datetime.now(UTC)),
            valid_to=kwargs.get("valid_to", datetime.now(UTC) + timedelta(days=30)),
        )
        for availability in kwargs.get("availabilities", []):
            schedule.availabilities.create(**availability)
        return schedule

    def create_availability(self, **kwargs):
        from care.emr.models import Availability

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
                        "day_of_week": 1,
                        "start_time": "09:00:00",
                        "end_time": "13:00:00",
                    }
                ],
            ),
        )

    def generate_availability_data(self, **kwargs):
        """Helper to generate valid availability data."""
        return {
            "name": "Morning Slot",
            "slot_type": SlotTypeOptions.appointment.value,
            "slot_size_in_minutes": 30,
            "tokens_per_slot": 1,
            "create_tokens": True,
            "reason": "Regular schedule",
            "availability": [
                {
                    "day_of_week": 1,
                    "start_time": "09:00:00",
                    "end_time": "13:00:00",
                }
            ],
            **kwargs,
        }

    def test_create_availability_with_permissions(self):
        """Users with can_write_user_schedule permission can create availability."""
        permissions = [UserSchedulePermissions.can_write_user_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        availability_data = self.generate_availability_data()
        response = self.client.post(self.base_url, availability_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], availability_data["name"])

    def test_create_availability_without_permissions(self):
        """Users without can_write_user_schedule permission cannot create availability."""
        availability_data = self.generate_availability_data()
        response = self.client.post(self.base_url, availability_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_availability_with_permissions(self):
        """Users with can_write_user_schedule permission can delete availability."""
        permissions = [
            UserSchedulePermissions.can_list_user_schedule.name,
            UserSchedulePermissions.can_write_user_schedule.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        availability = self.create_availability()
        delete_url = self._get_availability_url(availability.external_id)
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_availability_without_permissions(self):
        """Users without can_write_user_schedule permission cannot delete availability."""
        permissions = [UserSchedulePermissions.can_list_user_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        availability = self.create_availability()
        delete_url = self._get_availability_url(availability.external_id)
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_availability_without_queryset_list_permissions(self):
        """Users without can_list_user_schedule permission cannot delete availability."""
        availability = self.create_availability()
        delete_url = self._get_availability_url(availability.external_id)
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_availability_with_future_bookings(self):
        """Users cannot delete availability with future bookings."""
        permissions = [
            UserSchedulePermissions.can_list_user_schedule.name,
            UserSchedulePermissions.can_write_user_schedule.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        availability = self.create_availability()
        token_slot = TokenSlot.objects.create(
            resource=self.resource,
            availability=availability,
            start_datetime=datetime.now(UTC) + timedelta(days=4),
            end_datetime=datetime.now(UTC) + timedelta(days=5),
        )
        TokenBooking.objects.create(
            token_slot=token_slot,
            patient=self.create_patient(),
            booked_by=self.user,
        )
        token_slot.allocated = 1
        token_slot.save()
        delete_url = self._get_availability_url(availability.external_id)
        response = self.client.delete(delete_url)
        self.assertContains(
            response,
            status_code=400,
            text="Cannot delete availability as there are future bookings associated with it",
        )

    def test_create_availability_validate_availability(self):
        """Test validation rules for overlapping time ranges when creating availability slots."""
        permissions = [UserSchedulePermissions.can_write_user_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        # Try to create availability with overlapping time ranges for same day
        data = self.generate_availability_data(
            availability=[
                {
                    "day_of_week": 1,  # Monday
                    "start_time": "09:00:00",
                    "end_time": "13:00:00",
                },
                {
                    "day_of_week": 1,  # Same day (Monday)
                    "start_time": "12:00:00",  # Overlaps with previous range
                    "end_time": "17:00:00",
                },
            ]
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertContains(
            response,
            "Availability time ranges are overlapping",
            status_code=400,
        )

        # Verify that non-overlapping ranges on same day are allowed
        data = self.generate_availability_data(
            availability=[
                {
                    "day_of_week": 1,
                    "start_time": "09:00:00",
                    "end_time": "12:00:00",
                },
                {
                    "day_of_week": 1,
                    "start_time": "13:00:00",  # No overlap
                    "end_time": "17:00:00",
                },
            ]
        )

        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify that overlapping times on different days are allowed
        data = self.generate_availability_data(
            availability=[
                {
                    "day_of_week": 1,  # Monday
                    "start_time": "09:00:00",
                    "end_time": "17:00:00",
                },
                {
                    "day_of_week": 2,  # Tuesday
                    "start_time": "09:00:00",  # Same time range but different day
                    "end_time": "17:00:00",
                },
            ]
        )

        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_availability_validate_slot_type(self):
        """Test validation rules for different slot types when creating availability slots."""
        permissions = [UserSchedulePermissions.can_write_user_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        # Test appointment type without slot_size_in_minutes
        data = self.generate_availability_data(
            slot_type=SlotTypeOptions.appointment.value,
            slot_size_in_minutes=None,
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertContains(
            response,
            "Slot size in minutes is required for appointment slots",
            status_code=400,
        )

        # Test appointment type without tokens_per_slot
        data = self.generate_availability_data(
            slot_type=SlotTypeOptions.appointment.value,
            tokens_per_slot=None,
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertContains(
            response,
            "Tokens per slot is required for appointment slots",
            status_code=400,
        )

        # Test open slot type (should accept without slot_size and tokens)
        data = self.generate_availability_data(
            slot_type=SlotTypeOptions.open.value,
            slot_size_in_minutes=30,  # These should be ignored
            tokens_per_slot=1,  # These should be ignored
        )

        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["slot_size_in_minutes"])
        self.assertIsNone(response.data["tokens_per_slot"])
