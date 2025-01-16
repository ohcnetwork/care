from datetime import datetime, timedelta

from django.urls import reverse
from rest_framework import status

from care.emr.resources.scheduling.schedule.spec import SlotTypeOptions
from care.security.permissions.user_schedule import UserSchedulePermissions
from care.utils.tests.base import CareAPITestBase


class TestScheduleViewSet(CareAPITestBase):
    def setUp(self):
        from care.emr.models import SchedulableUserResource

        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.client.force_authenticate(user=self.user)

        self.base_url = reverse(
            "schedule-list", kwargs={"facility_external_id": self.facility.external_id}
        )
        self.resource = SchedulableUserResource.objects.create(
            user=self.user,
            facility=self.facility,
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
            valid_from=kwargs.get("valid_from", datetime.now()),
            valid_to=kwargs.get("valid_to", datetime.now() + timedelta(days=30)),
        )
        for availability in kwargs.get("availabilities", []):
            schedule.availabilities.create(**availability)
        return schedule

    def generate_schedule_data(self, **kwargs):
        """Helper to generate valid schedule data."""
        valid_from = datetime.now()
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

    # CREATE TESTS
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

        valid_from = datetime.now()
        valid_to = valid_from - timedelta(days=1)  # Invalid: end before start

        schedule_data = self.generate_schedule_data(
            valid_from=valid_from.isoformat(), valid_to=valid_to.isoformat()
        )
        response = self.client.post(self.base_url, schedule_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertContains(
            response, "Valid from cannot be greater than valid to", status_code=400
        )

    # UPDATE TESTS
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

    def test_update_schedule_validity_with_booking_outside_validity(self):
        pass

    def test_delete_schedule_with_bookings(self):
        pass

    def test_delete_availability_with_bookings(self):
        pass


class TestAvailabilityExceptionsViewSet(CareAPITestBase):
    def setUp(self):
        from care.emr.models import SchedulableUserResource

        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.client.force_authenticate(user=self.user)

        self.base_url = reverse(
            "schedule-exceptions-list",
            kwargs={"facility_external_id": self.facility.external_id},
        )
        self.resource = SchedulableUserResource.objects.create(
            user=self.user,
            facility=self.facility,
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

        valid_from = datetime.now().date()
        valid_to = (datetime.now() + timedelta(days=1)).date()
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
        valid_from = datetime.now().date()
        valid_to = (datetime.now() + timedelta(days=1)).date()

        return {
            "user": str(self.user.external_id),
            "reason": "Out of office",
            "valid_from": valid_from.isoformat(),
            "valid_to": valid_to.isoformat(),
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            **kwargs,
        }

    # LIST TESTS
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

    # CREATE TESTS
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

    # UPDATE TESTS
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

    # DELETE TESTS
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
        pass


class TestAvailabilityViewSet(CareAPITestBase):
    def setUp(self):
        from care.emr.models import SchedulableUserResource

        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.client.force_authenticate(user=self.user)
        self.resource = SchedulableUserResource.objects.create(
            user=self.user, facility=self.facility
        )
        self.schedule = self.create_schedule()

        self.base_url = reverse(
            "schedule-availability-list",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "schedule_external_id": self.schedule.external_id,
            },
        )
        self.resource = SchedulableUserResource.objects.create(
            user=self.user,
            facility=self.facility,
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
            valid_from=kwargs.get("valid_from", datetime.now()),
            valid_to=kwargs.get("valid_to", datetime.now() + timedelta(days=30)),
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
            create_tokens=kwargs.get("create_tokens", True),
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

    def test_delete_availability_with_bookings(self):
        pass
