from datetime import datetime, time

from freezegun import freeze_time
from pydantic import BaseModel, ValidationError
from requests import Response
from rest_framework import status
from rest_framework.test import APITestCase

from care.facility.models.schedule import (
    Availability,
    SchedulableResource,
    Schedule,
    ScheduleException,
    SlotType,
)
from care.users.models import User
from care.utils.tests.test_utils import TestUtils


@freeze_time("2024-11-01")
class TestAvailability(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)

        cls.user = cls.create_user(
            "staff", district=cls.district, local_body=cls.local_body
        )

        cls.facility = cls.create_facility(cls.user, cls.district, cls.local_body)
        cls.doctor_user = cls.create_user(
            "doctor",
            district=cls.district,
            local_body=cls.local_body,
            user_type=User.TYPE_VALUE_MAP["Doctor"],
            home_facility=cls.facility,
        )

        cls.schedulable_resource = SchedulableResource.objects.create(
            facility=cls.facility, resource=cls.doctor_user
        )
        cls.schedule = Schedule.objects.create(
            resource=cls.schedulable_resource,
            valid_from="2024-11-01",
            valid_to="2024-11-30",
        )

        # for monday to friday, availability for appointment 10-12 and open slots 14-16

        Availability.objects.create(
            schedule=cls.schedule,
            slot_type=SlotType.APPOINTMENT,
            slot_size_in_minutes=30,
            tokens_per_slot=10,
            days_of_week=[1, 2, 3, 4, 5],
            start_time=time(hour=10),
            end_time=time(hour=12),
        )
        Availability.objects.create(
            schedule=cls.schedule,
            slot_type=SlotType.OPEN,
            slot_size_in_minutes=0,
            tokens_per_slot=0,
            days_of_week=[1, 2, 3, 4, 5],
            start_time=time(hour=14),
            end_time=time(hour=16),
        )

        # he is on leave from 2024-11-05 to 2024-11-07
        ScheduleException.objects.create(
            resource=cls.schedulable_resource,
            is_available=False,
            slot_size_in_minutes=0,
            tokens_per_slot=0,
            datetime_range=(datetime(2024, 11, 5), datetime(2024, 11, 7)),
        )

        # he compensates for appointment on 2024-11-09 Saturday from 10-12
        ScheduleException.objects.create(
            resource=cls.schedulable_resource,
            is_available=True,
            slot_size_in_minutes=0,
            tokens_per_slot=0,
            datetime_range=(
                datetime(2024, 11, 9, hour=10),
                datetime(2024, 11, 9, hour=12),
            ),
        )

    def get_url(self, entry_id=None, action=None):
        base_url = f"/api/v1/facility/{self.facility.external_id}/schedule/"
        if entry_id is not None:
            base_url += f"{entry_id}/"
        if action is not None:
            base_url += f"{action}/"
        return base_url

    def get_list_response_schema(self):
        individual_response_schema = self.get_response_schema()

        class ScheduleListResponseSchema(BaseModel):
            count: int
            next: str | None
            previous: str | None
            results: list[individual_response_schema]

        return ScheduleListResponseSchema

    def get_response_schema(self):
        class AvailabilityResponseSchema(BaseModel):
            id: str
            name: str
            slot_type: int
            slot_size_in_minutes: int
            tokens_per_slot: int
            days_of_week: list[int]
            start_time: str
            end_time: str

        class ScheduleResponseSchema(BaseModel):
            id: str
            name: str
            valid_from: str
            valid_to: str
            availability: list[AvailabilityResponseSchema]

        return ScheduleResponseSchema

    def assert_response_schema(self, response: Response, schema: BaseModel):
        try:
            schema.validate(response.json())
        except ValidationError as e:
            raise e

    def test_create_schedule(self):
        # test create schedule for doctor user in december month
        data = {
            "name": "test schedule",
            "doctor_username": self.doctor_user.username,
            "valid_from": "2024-12-01",
            "valid_to": "2024-12-31",
            "availability": [
                {
                    "name": "appointment",
                    "slot_type": SlotType.APPOINTMENT.label,
                    "slot_size_in_minutes": 30,
                    "tokens_per_slot": 10,
                    "days_of_week": [1, 2, 3, 4, 5],
                    "start_time": "10:00",
                    "end_time": "12:00",
                },
                {
                    "name": "open",
                    "slot_type": SlotType.OPEN.label,
                    "start_time": "14:00",
                    "end_time": "16:00",
                    "days_of_week": [1, 2, 3, 4, 5],
                },
            ],
        }
        response = self.client.post(self.get_url(), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # check if the response is as per the spec
        response_json_schema = self.get_response_schema()
        self.assert_response_schema(response, response_json_schema)

    def test_delete_availability(self):
        new_availability = Availability.objects.create(
            schedule=self.schedule,
            name="new availability",
            slot_type=SlotType.APPOINTMENT,
            slot_size_in_minutes=30,
            tokens_per_slot=10,
            days_of_week=[1, 2, 3, 4, 5],
            start_time=time(hour=10),
            end_time=time(hour=12),
        )
        response = self.client.delete(
            self.get_url(
                self.schedule.external_id,
                f"availability/{new_availability.external_id}",
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_update_availability(self):
        availability_1 = self.schedule.availability_set.first()
        availability_count = self.schedule.availability_set.count()
        existing_availability_external_ids = list(
            self.schedule.availability_set.all().values_list("external_id", flat=True)
        )
        data = {
            "availability": [
                {
                    "external_id": availability_1.external_id,
                    "name": "appointment 2",
                    "slot_size_in_minutes": 45,
                    "tokens_per_slot": 15,
                },
                {
                    "name": "open 2",
                    "start_time": "15:00",
                    "end_time": "17:00",
                },
            ],
        }
        url = self.get_url(self.schedule.external_id)
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check if the response is as per the spec
        response_json_schema = self.get_response_schema()
        self.assert_response_schema(response, response_json_schema)

        # check if the availability is updated
        availability_1.refresh_from_db()
        self.assertEqual(availability_1.slot_size_in_minutes, 45)
        # check if the newly added availability is also present
        new_availability_external_ids = list(
            self.schedule.availability_set.all().values_list("external_id", flat=True)
        )
        self.assertEqual(self.schedule.availability_set.count(), availability_count + 1)
        self.assertTrue(
            all(
                availability_external_id in new_availability_external_ids
                for availability_external_id in existing_availability_external_ids
            )
        )

    def test_list_schedule(self):
        url = self.get_url()
        filter_params = {
            "valid_from": "2024-11-01",
            "valid_to": "2024-11-30",
            "doctor_username": self.doctor_user.username,
        }

        response = self.client.get(url, filter_params)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # check if the response is as per the spec
        response_json_schema = self.get_list_response_schema()
        self.assert_response_schema(response, response_json_schema)

        doctor_username = filter_params.pop("doctor_username")
        doctor = User.objects.get(username=doctor_username)
        schedules = Schedule.objects.filter_by_resource(doctor).filter(**filter_params)
        self.assertEqual(response.json()["count"], schedules.count())
