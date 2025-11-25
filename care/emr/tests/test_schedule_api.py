from datetime import UTC, datetime, timedelta

from django.conf import settings
from django.test.utils import ignore_warnings
from django.urls import reverse
from model_bakery import baker

from care.emr.models import (
    Availability,
    ChargeItemDefinition,
    SchedulableResource,
    Schedule,
    TokenBooking,
    TokenSlot,
)
from care.emr.models.location import FacilityLocation, FacilityLocationOrganization
from care.emr.resources.scheduling.schedule.spec import (
    SchedulableResourceTypeOptions,
    SlotTypeOptions,
)
from care.emr.resources.scheduling.slot.spec import (
    CANCELLED_STATUS_CHOICES,
    BookingStatusChoices,
)
from care.security.permissions.charge_item_definition import (
    ChargeItemDefinitionPermissions,
)
from care.security.permissions.schedule import SchedulePermissions
from care.utils.tests.base import CareAPITestBase


@ignore_warnings(category=RuntimeWarning, message=r".*received a naive datetime.*")
class TestScheduleViewSet(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.superuser = self.create_super_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(
            facility=self.facility, org_type="root"
        )
        self.resource = SchedulableResource.objects.create(
            resource_type=SchedulableResourceTypeOptions.practitioner.value,
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
        self.availability = self.generate_availiability()
        self.slot = self.create_slot()

        self.base_url = reverse(
            "schedule-list", kwargs={"facility_external_id": self.facility.external_id}
        )
        self.healthcare_services = self.create_healthcare_service(
            facility=self.facility
        )
        self.location = self.create_facility_location(
            facility=self.facility, facility_organization=self.organization
        )
        self.client.force_authenticate(user=self.user)

    def _get_schedule_url(self, schedule_id):
        """Helper to get the detail URL for a specific schedule."""
        return reverse(
            "schedule-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": schedule_id,
            },
        )

    def get_set_charge_item_defintion_url(self, schedule_external_id):
        """Helper to get the URL for set charge item defintion"""

        return reverse(
            "schedule-set-charge-item-definition",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": schedule_external_id,
            },
        )

    def create_schedule(self, **kwargs):
        from care.emr.models import Schedule

        schedule = Schedule.objects.create(
            resource=kwargs.get("resource", self.resource),
            name=kwargs.get("name", "Test Schedule"),
            valid_from=kwargs.get("valid_from", datetime.now(UTC)),
            valid_to=kwargs.get("valid_to", datetime.now(UTC) + timedelta(days=30)),
        )
        for availability in kwargs.get("availabilities", []):
            schedule.availabilities.create(**availability)
        return schedule

    def create_slot(self, **kwargs):
        data = {
            "resource": kwargs.get("resource", self.resource),
            "availability": kwargs.get("availability", self.availability),
            "start_datetime": datetime.now(UTC) + timedelta(minutes=30),
            "end_datetime": datetime.now(UTC) + timedelta(minutes=60),
            "allocated": 0,
        }
        data.update(kwargs)
        return TokenSlot.objects.create(**data)

    def create_booking(self, **kwargs):
        data = {
            "token_slot": kwargs.get("token_slot", self.slot),
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
        valid_from = datetime.now(UTC).replace(tzinfo=None)
        valid_to = (datetime.now(UTC) + timedelta(minutes=30)).replace(tzinfo=None)

        return {
            "resource_type": kwargs.get(
                "resource_type", SchedulableResourceTypeOptions.practitioner.value
            ),
            "resource_id": kwargs.get("resource_id", str(self.user.external_id)),
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

    def generate_availiability(self, **kwargs):
        return Availability.objects.create(
            schedule=kwargs.get("schedule", self.schedule),
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

    def create_healthcare_service(self, **kwargs):
        return baker.make("emr.HealthcareService", **kwargs)

    def create_facility_location(self, facility, facility_organization, **kwargs):
        location = baker.make(FacilityLocation, facility=facility, **kwargs)
        baker.make(
            FacilityLocationOrganization,
            location=location,
            organization=facility_organization,
        )
        return location

    # LIST TESTS
    def test_list_schedule_with_permissions(self):
        """Users with can_list_user_schedule permission can list schedules."""
        permissions = [SchedulePermissions.can_list_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        response = self.client.get(
            self.base_url,
            {
                "resource_type": SchedulableResourceTypeOptions.practitioner.value,
                "resource_id": str(self.user.external_id),
            },
        )
        self.assertEqual(response.status_code, 200)

    def test_list_schedule_without_permissions(self):
        """Users without can_list_user_schedule permission cannot list schedules."""
        response = self.client.get(
            self.base_url,
            {
                "resource_type": SchedulableResourceTypeOptions.practitioner.value,
                "resource_id": str(self.user.external_id),
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to list schedule", response.data["detail"]
        )

    def test_list_schedule_filtered_by_month_range(self):
        """Test various valid_from and valid_to edge cases"""

        permissions = [SchedulePermissions.can_list_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        filter_from = datetime(2025, 6, 1, 0, 0, tzinfo=UTC)
        filter_to = filter_from + timedelta(days=29)

        within_range = self.create_schedule(valid_from=filter_from, valid_to=filter_to)

        left_overlap = self.create_schedule(
            valid_from=filter_from - timedelta(days=5), valid_to=filter_to
        )

        right_overlap = self.create_schedule(
            valid_from=filter_from, valid_to=filter_to + timedelta(days=5)
        )

        outside_range = self.create_schedule(
            valid_from=filter_to + timedelta(days=2),
            valid_to=filter_to + timedelta(days=20),
        )

        response = self.client.get(
            self.base_url,
            {
                "valid_from": filter_from.isoformat(),
                "valid_to": filter_to.isoformat(),
                "resource_type": SchedulableResourceTypeOptions.practitioner.value,
                "resource_id": str(self.user.external_id),
            },
            format="json",
        )

        self.assertContains(response, str(within_range.external_id), status_code=200)
        self.assertContains(response, str(left_overlap.external_id), status_code=200)
        self.assertContains(response, str(right_overlap.external_id), status_code=200)
        self.assertNotContains(
            response, str(outside_range.external_id), status_code=200
        )

    def test_list_schedule_for_resourcetype_healthcare_service(self):
        """Users with can_list_schedule permission can list schedules for healthcare service resources."""
        permissions = [SchedulePermissions.can_list_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        resource = SchedulableResource.objects.create(
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.healthcare_service.value,
            healthcare_service=self.healthcare_services,
        )
        schedule = Schedule.objects.create(
            resource=resource,
            name="Healthcare Service Schedule",
            valid_from=datetime.now(UTC) - timedelta(days=30),
            valid_to=datetime.now(UTC) + timedelta(days=30),
        )
        response = self.client.get(
            self.base_url,
            {
                "resource_type": SchedulableResourceTypeOptions.healthcare_service.value,
                "resource_id": str(self.healthcare_services.external_id),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], str(schedule.external_id))

    def list_schedule_for_resourcetype_location(self):
        """Users with can_list_schedule permission can list schedules for location resources."""
        permissions = [SchedulePermissions.can_list_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        resource = SchedulableResource.objects.create(
            facility=self.facility,
            resource_type=SchedulableResourceTypeOptions.location.value,
            location=self.location,
        )
        schedule = Schedule.objects.create(
            resource=resource,
            name="Location Schedule",
            valid_from=datetime.now(UTC) - timedelta(days=30),
            valid_to=datetime.now(UTC) + timedelta(days=30),
        )
        response = self.client.get(
            self.base_url,
            {
                "resource_type": SchedulableResourceTypeOptions.location.value,
                "resource_id": str(self.location.external_id),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], str(schedule.external_id))

    def test_list_schedule_without_proper_filters(self):
        """Users cannot list schedules without proper filters."""
        permissions = [SchedulePermissions.can_list_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        response = self.client.get(self.base_url, format="json")
        self.assertContains(
            response,
            "resource_type and resource_id are required",
            status_code=400,
        )

    def test_create_schedule_with_permissions(self):
        """Users with can_write_user_schedule permission can create schedules."""
        permissions = [SchedulePermissions.can_write_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        schedule_data = self.generate_schedule_data(
            valid_from=(datetime.now(UTC) + timedelta(minutes=30)).replace(tzinfo=None)
        )
        response = self.client.post(self.base_url, schedule_data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], schedule_data["name"])

    def test_create_schedule_without_permissions(self):
        """Users without can_write_user_schedule permission cannot create schedules."""
        schedule_data = self.generate_schedule_data(
            valid_from=(datetime.now(UTC) + timedelta(minutes=30)).replace(tzinfo=None)
        )
        response = self.client.post(self.base_url, schedule_data, format="json")
        self.assertEqual(response.status_code, 403)

    def test_create_schedule_with_overlapping_availability(self):
        """Schedule creation fails when availability sessions overlap"""
        permissions = [SchedulePermissions.can_write_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        schedule_data = self.generate_schedule_data(
            availabilities=[
                {
                    "name": "Availability 1",
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
                        },
                    ],
                },
                {
                    "name": "Availability 2",
                    "slot_type": SlotTypeOptions.appointment.value,
                    "slot_size_in_minutes": 30,
                    "tokens_per_slot": 1,
                    "create_tokens": True,
                    "reason": "Regular schedule",
                    "availability": [
                        {
                            "day_of_week": 1,
                            "start_time": "08:00:00",
                            "end_time": "10:00:00",
                        },
                    ],
                },
            ]
        )
        response = self.client.post(self.base_url, schedule_data, format="json")
        self.assertContains(
            response, "Availability time ranges are overlapping", status_code=400
        )

    def test_create_schedule_for_resource_type_healthcare_service_as_superuser(self):
        """Superusers can create schedules for healthcare service resources."""
        schedule_data = self.generate_schedule_data(
            resource_type=SchedulableResourceTypeOptions.healthcare_service.value,
            resource_id=str(self.healthcare_services.external_id),
            valid_from=(datetime.now(UTC) + timedelta(minutes=30)).replace(tzinfo=None),
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(self.base_url, schedule_data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], schedule_data["name"])

    def test_create_schedule_for_resource_type_healthcare_service_as_user_with_permissions(
        self,
    ):
        """Users with can_write_schedule permission can create schedules for healthcare service resources."""
        permissions = [SchedulePermissions.can_write_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        schedule_data = self.generate_schedule_data(
            resource_type=SchedulableResourceTypeOptions.healthcare_service.value,
            resource_id=str(self.healthcare_services.external_id),
            valid_from=(datetime.now(UTC) + timedelta(minutes=30)).replace(tzinfo=None),
        )
        response = self.client.post(self.base_url, schedule_data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], schedule_data["name"])

    def test_create_schedule_for_resource_type_healthcare_service_as_user_without_permissions(
        self,
    ):
        """Users without can_write_schedule permission cannot create schedules for healthcare service resources."""
        schedule_data = self.generate_schedule_data(
            resource_type=SchedulableResourceTypeOptions.healthcare_service.value,
            resource_id=str(self.healthcare_services.external_id),
            valid_from=(datetime.now(UTC) + timedelta(minutes=30)).replace(tzinfo=None),
        )
        response = self.client.post(self.base_url, schedule_data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to create schedule", response.data["detail"]
        )

    def test_create_schedule_with_invalid_healthcare_service(self):
        """Users cannot create schedules for healthcare services not part of the facility."""
        permissions = [SchedulePermissions.can_write_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        other_healthcare_service = self.create_healthcare_service()

        schedule_data = self.generate_schedule_data(
            resource_type=SchedulableResourceTypeOptions.healthcare_service.value,
            resource_id=str(other_healthcare_service.external_id),
            valid_from=(datetime.now(UTC) + timedelta(minutes=30)).replace(tzinfo=None),
        )
        response = self.client.post(self.base_url, schedule_data, format="json")
        self.assertContains(
            response,
            "Healthcare Service is not part of the facility",
            status_code=400,
        )

    def test_create_schedule_for_resource_type_location_as_superuser(self):
        """Superusers can create schedules for location resources."""
        self.client.force_authenticate(user=self.superuser)
        schedule_data = self.generate_schedule_data(
            resource_type=SchedulableResourceTypeOptions.location.value,
            resource_id=str(self.location.external_id),
            valid_from=(datetime.now(UTC) + timedelta(minutes=30)).replace(tzinfo=None),
        )
        response = self.client.post(self.base_url, schedule_data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], schedule_data["name"])

    def test_create_schedule_for_resource_type_location_as_user_with_permissions(self):
        """Users with can_write_schedule permission can create schedules for location resources."""
        permissions = [SchedulePermissions.can_write_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        schedule_data = self.generate_schedule_data(
            resource_type=SchedulableResourceTypeOptions.location.value,
            resource_id=str(self.location.external_id),
            valid_from=(datetime.now(UTC) + timedelta(minutes=30)).replace(tzinfo=None),
        )
        response = self.client.post(self.base_url, schedule_data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], schedule_data["name"])

    def test_create_schedule_for_resource_type_location_as_user_without_permissions(
        self,
    ):
        """Users without can_write_schedule permission cannot create schedules for location resources."""
        schedule_data = self.generate_schedule_data(
            resource_type=SchedulableResourceTypeOptions.location.value,
            resource_id=str(self.location.external_id),
            valid_from=(datetime.now(UTC) + timedelta(minutes=30)).replace(tzinfo=None),
        )
        response = self.client.post(self.base_url, schedule_data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to create schedule", response.data["detail"]
        )

    def test_create_schedule_with_invalid_location(self):
        """Users cannot create schedules for locations not part of the facility."""
        permissions = [SchedulePermissions.can_write_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        invalid_facility = self.create_facility(user=self.user)
        invalid_facility_organization = self.create_facility_organization(
            facility=invalid_facility, org_type="root"
        )
        other_location = self.create_facility_location(
            facility=invalid_facility,
            facility_organization=invalid_facility_organization,
        )

        schedule_data = self.generate_schedule_data(
            resource_type=SchedulableResourceTypeOptions.location.value,
            resource_id=str(other_location.external_id),
            valid_from=(datetime.now(UTC) + timedelta(minutes=30)).replace(tzinfo=None),
        )
        response = self.client.post(self.base_url, schedule_data, format="json")
        self.assertContains(
            response,
            "Location is not part of the facility",
            status_code=400,
        )

    def test_create_schedule_with_user_not_part_of_facility(self):
        """Users cannot write schedules for user not belonging to the facility."""
        permissions = [SchedulePermissions.can_write_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        user = self.create_user()
        schedule_data = self.generate_schedule_data(
            resource_id=user.external_id,
            valid_from=(datetime.now(UTC) + timedelta(minutes=30)).replace(tzinfo=None),
        )
        response = self.client.post(self.base_url, schedule_data, format="json")
        self.assertContains(
            response, "Schedule User is not part of the facility", status_code=400
        )

    def test_create_schedule_with_valid_from_date_less_than_current_date(self):
        """Users cannot create schedule with valid_from date less than now date"""
        permissions = [SchedulePermissions.can_write_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        schedule_data = self.generate_schedule_data(
            valid_from=(datetime.now(UTC) - timedelta(minutes=30)).replace(tzinfo=None)
        )
        response = self.client.post(self.base_url, schedule_data, format="json")
        self.assertContains(
            response,
            "Date cannot be before the current date",
            status_code=400,
        )

    def test_create_schedule_with_valid_to_date_less_than_current_date(self):
        """Users cannot create schedule with valid_to date less than now date"""
        permissions = [SchedulePermissions.can_write_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        schedule_data = self.generate_schedule_data(
            valid_to=(datetime.now(UTC) - timedelta(minutes=30)).replace(tzinfo=None)
        )
        response = self.client.post(self.base_url, schedule_data, format="json")
        self.assertContains(
            response,
            "Date cannot be before the current date",
            status_code=400,
        )

    def test_create_schedule_with_valid_to_date_less_than_valid_from_date(self):
        """Users cannot create schedule with valid_to date less than valid_from date"""
        permissions = [SchedulePermissions.can_write_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        schedule_data = self.generate_schedule_data(
            valid_to=(datetime.now(UTC) + timedelta(minutes=10)).replace(tzinfo=None),
            valid_from=(datetime.now(UTC) + timedelta(minutes=30)).replace(tzinfo=None),
        )
        response = self.client.post(self.base_url, schedule_data, format="json")
        self.assertContains(
            response,
            "Valid from cannot be greater than valid to",
            status_code=400,
        )

    def test_update_schedule_with_permissions(self):
        """Users with can_write_user_schedule permission can update schedules."""
        permissions = [
            SchedulePermissions.can_write_schedule.name,
            SchedulePermissions.can_list_schedule.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        updated_data = {
            "name": "Updated Schedule Name",
            "valid_from": self.schedule.valid_from,
            "valid_to": self.schedule.valid_to,
        }
        update_url = self._get_schedule_url(self.schedule.external_id)
        response = self.client.put(update_url, updated_data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Updated Schedule Name")

    def test_update_schedule_without_permissions(self):
        """Users without can_write_user_schedule permission cannot update schedules."""
        # First create a schedule with permissions
        permissions = [
            SchedulePermissions.can_list_schedule.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        updated_data = {
            "name": "Updated Schedule Name",
            "valid_from": self.schedule.valid_from,
            "valid_to": self.schedule.valid_to,
        }
        update_url = self._get_schedule_url(self.schedule.external_id)
        response = self.client.put(update_url, updated_data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to update schedule",
            response.data["detail"],
        )

    def test_upadate_schedule_for_resource_type_healthcare_service_as_superuser(self):
        """Superusers can update schedules for healthcare service resources."""
        self.client.force_authenticate(user=self.superuser)
        schedule_resource = SchedulableResource.objects.create(
            resource_type=SchedulableResourceTypeOptions.healthcare_service.value,
            facility=self.facility,
            healthcare_service=self.healthcare_services,
        )
        healthcare_service_schedule = self.create_schedule(resource=schedule_resource)
        updated_data = {
            "name": "Updated Schedule Name",
            "valid_from": self.schedule.valid_from,
            "valid_to": self.schedule.valid_to,
        }
        update_url = self._get_schedule_url(healthcare_service_schedule.external_id)
        response = self.client.put(update_url, updated_data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Updated Schedule Name")

    def test_upadate_schedule_for_resource_type_healthcare_service_as_user_with_permissions(
        self,
    ):
        """Users with can_write_schedule permission can update schedules for healthcare service resources."""
        permissions = [
            SchedulePermissions.can_write_schedule.name,
            SchedulePermissions.can_list_schedule.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        schedule_resource = SchedulableResource.objects.create(
            resource_type=SchedulableResourceTypeOptions.healthcare_service.value,
            facility=self.facility,
            healthcare_service=self.healthcare_services,
        )
        healthcare_service_schedule = self.create_schedule(resource=schedule_resource)
        updated_data = {
            "name": "Updated Schedule Name",
            "valid_from": self.schedule.valid_from,
            "valid_to": self.schedule.valid_to,
        }
        update_url = self._get_schedule_url(healthcare_service_schedule.external_id)
        response = self.client.put(update_url, updated_data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Updated Schedule Name")

    def test_upadate_schedule_for_resource_type_healthcare_service_as_user_without_permissions(
        self,
    ):
        """Users without can_write_schedule permission cannot update schedules for healthcare service resources."""
        schedule_resource = SchedulableResource.objects.create(
            resource_type=SchedulableResourceTypeOptions.healthcare_service.value,
            facility=self.facility,
            healthcare_service=self.healthcare_services,
        )
        healthcare_service_schedule = self.create_schedule(resource=schedule_resource)
        updated_data = {
            "name": "Updated Schedule Name",
            "valid_from": self.schedule.valid_from,
            "valid_to": self.schedule.valid_to,
        }
        update_url = self._get_schedule_url(healthcare_service_schedule.external_id)
        response = self.client.put(update_url, updated_data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to update schedule",
            response.data["detail"],
        )

    def test_upadate_schedule_for_resource_type_location_as_superuser(self):
        """Superusers can update schedules for location resources."""
        self.client.force_authenticate(user=self.superuser)
        schedule_resource = SchedulableResource.objects.create(
            resource_type=SchedulableResourceTypeOptions.location.value,
            facility=self.facility,
            location=self.location,
        )
        location_schedule = self.create_schedule(resource=schedule_resource)
        updated_data = {
            "name": "Updated Schedule Name",
            "valid_from": self.schedule.valid_from,
            "valid_to": self.schedule.valid_to,
        }
        update_url = self._get_schedule_url(location_schedule.external_id)
        response = self.client.put(update_url, updated_data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Updated Schedule Name")

    def test_upadate_schedule_for_resource_type_location_as_user_with_permissions(self):
        """Users with can_write_schedule permission can update schedules for location resources."""
        permissions = [
            SchedulePermissions.can_write_schedule.name,
            SchedulePermissions.can_list_schedule.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        schedule_resource = SchedulableResource.objects.create(
            resource_type=SchedulableResourceTypeOptions.location.value,
            facility=self.facility,
            location=self.location,
        )
        location_schedule = self.create_schedule(resource=schedule_resource)
        updated_data = {
            "name": "Updated Schedule Name",
            "valid_from": self.schedule.valid_from,
            "valid_to": self.schedule.valid_to,
        }
        update_url = self._get_schedule_url(location_schedule.external_id)
        response = self.client.put(update_url, updated_data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Updated Schedule Name")

    def test_upadate_schedule_for_resource_type_location_as_user_without_permissions(
        self,
    ):
        """Users without can_write_schedule permission cannot update schedules for location resources."""
        schedule_resource = SchedulableResource.objects.create(
            resource_type=SchedulableResourceTypeOptions.location.value,
            facility=self.facility,
            location=self.location,
        )
        location_schedule = self.create_schedule(resource=schedule_resource)
        updated_data = {
            "name": "Updated Schedule Name",
            "valid_from": self.schedule.valid_from,
            "valid_to": self.schedule.valid_to,
        }
        update_url = self._get_schedule_url(location_schedule.external_id)
        response = self.client.put(update_url, updated_data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to update schedule",
            response.data["detail"],
        )

    # DELETE TESTS
    def test_delete_schedule_with_permissions(self):
        """Users with can_write_user_schedule permission can delete schedules."""
        permissions = [
            SchedulePermissions.can_write_schedule.name,
            SchedulePermissions.can_list_schedule.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        delete_url = self._get_schedule_url(self.schedule.external_id)
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, 204)

        self.availability.refresh_from_db()
        self.slot.refresh_from_db()

        self.assertTrue(self.availability.deleted)
        self.assertTrue(self.slot.deleted)

    def test_delete_schedule_without_permissions(self):
        """Users without can_write_user_schedule permission cannot delete schedules."""
        # First create a schedule with permissions
        permissions = [
            SchedulePermissions.can_list_schedule.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        delete_url = self._get_schedule_url(self.schedule.external_id)
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, 403)

    def test_update_schedule_validity_with_booking_within_new_validity(self):
        """Test that schedule validity can be updated when bookings fall within the new validity period."""
        permissions = [
            SchedulePermissions.can_write_schedule.name,
            SchedulePermissions.can_list_schedule.name,
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
        self.assertEqual(response.status_code, 200)

    def test_update_schedule_validity_with_booking_outside_new_validity(self):
        """Test that schedule validity cannot be updated when bookings fall outside the new validity period."""
        permissions = [
            SchedulePermissions.can_write_schedule.name,
            SchedulePermissions.can_list_schedule.name,
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
            SchedulePermissions.can_write_schedule.name,
            SchedulePermissions.can_list_schedule.name,
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
            SchedulePermissions.can_write_schedule.name,
            SchedulePermissions.can_list_schedule.name,
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
        self.assertEqual(response.status_code, 204)

    def test_retrieve_schedule_with_permissions(self):
        """Users with can_list_user_schedule permission can retrieve schedules."""
        permissions = [SchedulePermissions.can_list_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        retrieve_url = self._get_schedule_url(self.schedule.external_id)
        response = self.client.get(retrieve_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], self.schedule.name)

    def test_retrieve_schedule_without_permissions(self):
        """Users without can_list_user_schedule permission cannot retrieve schedules."""
        retrieve_url = self._get_schedule_url(self.schedule.external_id)
        response = self.client.get(retrieve_url)
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to list schedule", response.data["detail"]
        )

    def test_retrieve_schedule_as_superuser(self):
        """Superusers can retrieve any schedule."""
        self.client.force_authenticate(user=self.superuser)
        retrieve_url = self._get_schedule_url(self.schedule.external_id)
        response = self.client.get(retrieve_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], self.schedule.name)

    # Testcases for set chargeitem defintion

    def test_set_chargeitem_definition_with_permissions(self):
        """Users with can_write_user_schedule permission can set chargeitem definition."""
        permissions = [
            ChargeItemDefinitionPermissions.can_set_charge_item_definition.name
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        chargeitem_definition = ChargeItemDefinition.objects.create(
            description="General health consultation charge item",
            slug=f"f-{self.facility.external_id}-consultation",
            facility=self.facility,
        )
        set_chargeitem_url = reverse(
            "schedule-set-charge-item-definition",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": self.schedule.external_id,
            },
        )
        response = self.client.post(
            set_chargeitem_url,
            {
                "charge_item_definition": str(chargeitem_definition.slug),
                "re_visit_allowed_days": 30,
                "re_visit_charge_item_definition": str(chargeitem_definition.slug),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["charge_item_definition"]["id"],
            str(chargeitem_definition.external_id),
        )

    def test_set_chargeitem_definition_without_permissions(self):
        """Users without can_write_user_schedule permission cannot set chargeitem definition."""
        chargeitem_definition = ChargeItemDefinition.objects.create(
            description="General health consultation charge item",
            slug=f"f-{self.facility.external_id}-consultation",
            facility=self.facility,
        )
        set_chargeitem_url = reverse(
            "schedule-set-charge-item-definition",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": self.schedule.external_id,
            },
        )
        response = self.client.post(
            set_chargeitem_url,
            {
                "charge_item_definition": str(chargeitem_definition.slug),
                "re_visit_allowed_days": 30,
                "re_visit_charge_item_definition": None,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to set charge item definition",
            response.data["detail"],
        )

    def test_set_chargeitem_definition_with_invalid_chargeitem_definition(self):
        """Setting chargeitem definition fails with invalid chargeitem definition."""
        permissions = [
            ChargeItemDefinitionPermissions.can_set_charge_item_definition.name
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        set_chargeitem_url = reverse(
            "schedule-set-charge-item-definition",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": self.schedule.external_id,
            },
        )
        response = self.client.post(
            set_chargeitem_url,
            {
                "charge_item_definition": "invalid-slug",
                "re_visit_allowed_days": 30,
                "re_visit_charge_item_definition": None,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertIn(
            "No ChargeItemDefinition matches the given query.",
            response.data["errors"][0]["msg"],
        )


@ignore_warnings(category=RuntimeWarning, message=r".*received a naive datetime.*")
class TestAvailabilityExceptionsViewSet(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.resource = SchedulableResource.objects.create(
            resource_type=SchedulableResourceTypeOptions.practitioner.value,
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

        valid_from = kwargs.get("valid_from", datetime.now(UTC).date())
        valid_to = kwargs.get(
            "valid_to", (datetime.now(UTC) + timedelta(days=1)).date()
        )
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
            "resource_type": SchedulableResourceTypeOptions.practitioner.value,
            "resource_id": str(self.user.external_id),
            "reason": "Out of office",
            "valid_from": valid_from.isoformat(),
            "valid_to": valid_to.isoformat(),
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            **kwargs,
        }

    def test_list_exceptions_with_permissions(self):
        """Users with can_list_user_schedule permission can list exceptions."""
        permissions = [SchedulePermissions.can_list_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        response = self.client.get(
            self.base_url,
            {
                "resource_type": SchedulableResourceTypeOptions.practitioner.value,
                "resource_id": str(self.user.external_id),
            },
        )
        self.assertEqual(response.status_code, 200)

    def test_list_exceptions_without_permissions(self):
        """Users without can_list_user_schedule permission cannot list exceptions."""
        response = self.client.get(
            self.base_url,
            {
                "resource_type": SchedulableResourceTypeOptions.practitioner.value,
                "resource_id": str(self.user.external_id),
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to list schedule", response.data["detail"]
        )

    def test_list_exceptions_filtered_by_month_range(self):
        """Test various valid_from and valid_to edge cases"""

        permissions = [SchedulePermissions.can_list_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        filter_from = datetime(2025, 6, 1).date()
        filter_to = filter_from + timedelta(days=29)

        within_range = self.create_exception(valid_from=filter_from, valid_to=filter_to)

        left_overlap = self.create_exception(
            valid_from=filter_from - timedelta(days=5),
            valid_to=filter_to,
        )

        right_overlap = self.create_exception(
            valid_from=filter_from,
            valid_to=filter_to + timedelta(days=5),
        )

        outside_range = self.create_exception(
            valid_from=filter_to + timedelta(days=5),
            valid_to=filter_to + timedelta(days=25),
        )

        response = self.client.get(
            self.base_url,
            {
                "resource_type": SchedulableResourceTypeOptions.practitioner.value,
                "resource_id": str(self.user.external_id),
                "valid_from": filter_from.isoformat(),
                "valid_to": filter_to.isoformat(),
            },
            format="json",
        )

        self.assertContains(response, str(within_range.external_id), status_code=200)
        self.assertContains(response, str(left_overlap.external_id), status_code=200)
        self.assertContains(response, str(right_overlap.external_id), status_code=200)
        self.assertNotContains(
            response, str(outside_range.external_id), status_code=200
        )

    def test_create_exception_with_permissions(self):
        """Users with can_write_user_schedule permission can create exceptions."""
        permissions = [SchedulePermissions.can_write_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        exception_data = self.generate_exception_data()
        response = self.client.post(self.base_url, exception_data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["reason"], exception_data["reason"])

    def test_create_exception_without_permissions(self):
        """Users without can_write_user_schedule permission cannot create exceptions."""
        exception_data = self.generate_exception_data()
        response = self.client.post(self.base_url, exception_data, format="json")
        self.assertEqual(response.status_code, 403)

    def test_create_exception_with_invalid_user_resource(self):
        """Users with can_write_user_schedule permission can create exceptions."""
        permissions = [SchedulePermissions.can_write_schedule.name]
        role = self.create_role_with_permissions(permissions)

        user = self.create_user()
        facility = self.create_facility(user=user)
        organization = self.create_facility_organization(facility=facility)
        self.attach_role_facility_organization_user(organization, user, role)

        exception_data = self.generate_exception_data(resource_id=user.external_id)
        response = self.client.post(self.base_url, exception_data, format="json")
        self.assertContains(
            response, "Schedule User is not part of the facility", status_code=400
        )

    def test_create_exception_with_valid_from_date_less_than_current_date(self):
        """Users cannot create exception with valid_from date less than now date"""
        permissions = [SchedulePermissions.can_write_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        exception_data = self.generate_exception_data(
            valid_from=(datetime.now(UTC).date() - timedelta(days=1)).isoformat()
        )
        response = self.client.post(self.base_url, exception_data, format="json")
        self.assertContains(
            response,
            "Date cannot be before the current date",
            status_code=400,
        )

    def test_create_exception_with_valid_to_date_less_than_current_date(self):
        """Users cannot create exception with valid_to date less than now date"""
        permissions = [SchedulePermissions.can_write_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        exception_data = self.generate_exception_data(
            valid_to=(datetime.now(UTC).date() - timedelta(days=1)).isoformat()
        )
        response = self.client.post(self.base_url, exception_data, format="json")
        self.assertContains(
            response,
            "Date cannot be before the current date",
            status_code=400,
        )

    def test_create_exception_with_valid_to_date_less_than_valid_from_date(self):
        """Users cannot create exception with valid_to date less than now valid_from date"""
        permissions = [SchedulePermissions.can_write_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        exception_data = self.generate_exception_data(
            valid_to=(datetime.now(UTC).date() + timedelta(days=1)).isoformat(),
            valid_from=(datetime.now(UTC).date() + timedelta(days=4)).isoformat(),
        )
        response = self.client.post(self.base_url, exception_data, format="json")
        self.assertContains(
            response,
            "Valid from cannot be greater than valid to",
            status_code=400,
        )

    def test_delete_exception_with_permissions(self):
        """Users with can_write_user_schedule permission can delete exceptions."""
        permissions = [
            SchedulePermissions.can_write_schedule.name,
            SchedulePermissions.can_list_schedule.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        # First create an exception
        exception = self.create_exception()

        # Then delete it
        delete_url = self._get_exception_url(exception.external_id)
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, 204)

    def test_delete_exception_without_permissions(self):
        """Users without can_write_user_schedule permission cannot delete exceptions."""
        role = self.create_role_with_permissions([])
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        exception = self.create_exception()

        delete_url = self._get_exception_url(exception.external_id)
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, 403)

    def test_create_exception_with_bookings(self):
        """Test that creating an exception fails when there are conflicting bookings."""
        permissions = [SchedulePermissions.can_write_schedule.name]
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
        self.assertEqual(response.status_code, 400)
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
        self.resource = SchedulableResource.objects.create(
            resource_type=SchedulableResourceTypeOptions.practitioner.value,
            user=self.user,
            facility=self.facility,
        )
        self.schedule = self.create_schedule()
        self.availability = self.create_availability()
        self.slot = self.create_slot()

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
                    "day_of_week": 2,
                    "start_time": "09:00:00",
                    "end_time": "13:00:00",
                }
            ],
            **kwargs,
        }

    def test_create_availability_with_permissions(self):
        """Users with can_write_user_schedule permission can create availability."""
        permissions = [SchedulePermissions.can_write_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        availability_data = self.generate_availability_data()
        response = self.client.post(self.base_url, availability_data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], availability_data["name"])

    def test_create_availability_overlapping_with_existing_availabilities(self):
        """Users cannot create availability that overlaps with existing availabilities."""
        permissions = [SchedulePermissions.can_write_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        self.create_availability(
            availability=[
                {"day_of_week": 1, "start_time": "08:00:00", "end_time": "10:00:00"},
            ]
        )

        availability_data = self.generate_availability_data()
        response = self.client.post(self.base_url, availability_data, format="json")
        self.assertContains(
            response, "Availability time ranges are overlapping", status_code=400
        )

    def test_create_availability_not_overlapping_with_existing_availabilities(self):
        """Users can create availability that does not overlap with existing availabilities."""
        permissions = [SchedulePermissions.can_write_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        self.create_availability(
            availability=[
                {"day_of_week": 1, "start_time": "14:00:00", "end_time": "20:00:00"},
            ]
        )

        availability_data = self.generate_availability_data()
        response = self.client.post(self.base_url, availability_data, format="json")
        self.assertEqual(response.status_code, 200)

    def test_create_availability_without_permissions(self):
        """Users without can_write_user_schedule permission cannot create availability."""
        availability_data = self.generate_availability_data()
        response = self.client.post(self.base_url, availability_data, format="json")
        self.assertEqual(response.status_code, 403)

    def test_delete_availability_with_permissions(self):
        """Users with can_write_user_schedule permission can delete availability."""
        permissions = [
            SchedulePermissions.can_list_schedule.name,
            SchedulePermissions.can_write_schedule.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        delete_url = self._get_availability_url(self.availability.external_id)
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, 204)

        self.availability.refresh_from_db()
        self.slot.refresh_from_db()

        self.assertTrue(self.availability.deleted)
        self.assertTrue(self.slot.deleted)

    def test_delete_availability_without_permissions(self):
        """Users without can_write_user_schedule permission cannot delete availability."""
        permissions = [SchedulePermissions.can_list_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        delete_url = self._get_availability_url(self.availability.external_id)
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, 403)

    def test_delete_availability_without_queryset_list_permissions(self):
        """Users without can_list_user_schedule permission cannot delete availability."""
        delete_url = self._get_availability_url(self.availability.external_id)
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, 403)

    def test_delete_availability_with_future_bookings(self):
        """Users cannot delete availability with future bookings."""
        permissions = [
            SchedulePermissions.can_list_schedule.name,
            SchedulePermissions.can_write_schedule.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        token_slot = TokenSlot.objects.create(
            resource=self.resource,
            availability=self.availability,
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
        delete_url = self._get_availability_url(self.availability.external_id)
        response = self.client.delete(delete_url)
        self.assertContains(
            response,
            status_code=400,
            text="Cannot delete availability as there are future bookings associated with it",
        )

    def test_create_availability_validate_availability(self):
        """Test validation rules for overlapping time ranges when creating availability slots."""
        permissions = [SchedulePermissions.can_write_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        # Try to create availability with overlapping time ranges for same day
        data = self.generate_availability_data(
            availability=[
                {
                    "day_of_week": 2,  # Monday
                    "start_time": "09:00:00",
                    "end_time": "13:00:00",
                },
                {
                    "day_of_week": 2,  # Same day (Monday)
                    "start_time": "12:00:00",  # Overlaps with previous range
                    "end_time": "17:00:00",
                },
            ]
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertContains(
            response, "Availability time ranges are overlapping", status_code=400
        )
        # Verify that non-overlapping ranges on same day are allowed
        data = self.generate_availability_data(
            availability=[
                {
                    "day_of_week": 2,
                    "start_time": "09:00:00",
                    "end_time": "12:00:00",
                },
                {
                    "day_of_week": 2,
                    "start_time": "13:00:00",  # No overlap
                    "end_time": "17:00:00",
                },
            ]
        )

        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)

        # Verify that overlapping times on different days are allowed
        data = self.generate_availability_data(
            availability=[
                {
                    "day_of_week": 3,  # Tuesday
                    "start_time": "09:00:00",
                    "end_time": "17:00:00",
                },
                {
                    "day_of_week": 4,  # Wednesday
                    "start_time": "09:00:00",  # Same time range but different day
                    "end_time": "17:00:00",
                },
            ]
        )

        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)

    def test_create_availability_validate_duration_multiple_of_slot_size_in_minutes(
        self,
    ):
        """Test validation rules for ensuring availability duration is multiple of slot size in minutes."""
        permissions = [SchedulePermissions.can_write_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        # Try to create availability with duration not multiple of slot size
        data = self.generate_availability_data(
            availability=[
                {
                    "day_of_week": 2,  # Monday
                    "start_time": "09:00:00",
                    "end_time": "13:13:00",
                },
            ]
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertContains(
            response,
            "Availability duration must be a multiple of slot size in minutes",
            status_code=400,
        )

    def test_create_availability_start_time_greater_than_end_time(self):
        """Test validation rules for ensuring start time is before end time."""
        permissions = [SchedulePermissions.can_write_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        # Try to create availability with end time before start time
        data = self.generate_availability_data(
            availability=[
                {
                    "day_of_week": 1,  # Monday
                    "start_time": "13:00:00",
                    "end_time": "09:00:00",
                },
            ]
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertContains(
            response,
            "Start time must be earlier than end time",
            status_code=400,
        )

    def test_create_availability_total_slots_greater_than_max_slots(self):
        """Test validation rules for ensuring total_slots is not greater than maximum slots."""
        permissions = [SchedulePermissions.can_write_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        data = self.generate_availability_data(
            slot_size_in_minutes=10,
            availability=[
                {
                    "day_of_week": 1,
                    "start_time": "10:00:00",
                    "end_time": "22:00:00",
                },
            ],
        )
        expected_error = f"Too many slots per availability. Maximum allowed is {settings.MAX_SLOTS_PER_AVAILABILITY} slots per availability session."
        response = self.client.post(self.base_url, data, format="json")
        self.assertContains(
            response,
            expected_error,
            status_code=400,
        )

    def test_create_availability_total_slots_equal_to_max_slots(self):
        """Test validation rules for ensuring total_slots is equal to maximum slots."""
        permissions = [SchedulePermissions.can_write_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        data = self.generate_availability_data(
            slot_size_in_minutes=10,
            availability=[
                {
                    "day_of_week": 2,
                    "start_time": "09:00:00",
                    "end_time": "14:00:00",
                },
            ],
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)

    def test_create_availability_total_slots_less_than_to_max_slots(self):
        """Test validation rules for ensuring total_slots is equal to maximum slots."""
        permissions = [SchedulePermissions.can_write_schedule.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        data = self.generate_availability_data(
            slot_size_in_minutes=10,
            availability=[
                {
                    "day_of_week": 2,
                    "start_time": "09:00:00",
                    "end_time": "13:00:00",
                },
            ],
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)

    def test_create_availability_validate_slot_type(self):
        """Test validation rules for different slot types when creating availability slots."""
        permissions = [SchedulePermissions.can_write_schedule.name]
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
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["slot_size_in_minutes"])
        self.assertIsNone(response.data["tokens_per_slot"])
