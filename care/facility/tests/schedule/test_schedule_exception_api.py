from datetime import time

from freezegun import freeze_time
from pydantic import BaseModel, ValidationError
from requests import Response
from rest_framework import status
from rest_framework.test import APITestCase

from care.facility.models.schedule import (
    ScheduleException,
    SlotType,
)
from care.facility.tests.schedule.setup import ScheduleTestSetup
from care.utils.tests.test_utils import TestUtils


@freeze_time("2024-11-01")
class TestScheduleException(TestUtils, ScheduleTestSetup, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.setup_schedule()

    def get_url(self, entry_id=None, action=None):
        base_url = f"/api/v1/facility/{self.facility.external_id}/schedule_exceptions/"
        if entry_id is not None:
            base_url += f"{entry_id}/"
        if action is not None:
            base_url += f"{action}/"
        return base_url

    def get_response_schema(self):
        class ScheduleExceptionResponseSchema(BaseModel):
            id: str
            name: str
            is_available: bool
            valid_from: str
            valid_to: str
            start_time: str
            end_time: str
            slot_type: str
            slot_size_in_minutes: int
            tokens_per_slot: int

        return ScheduleExceptionResponseSchema

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
            "is_available": True,
            "valid_from": "2024-12-09",
            "valid_to": "2024-12-09",
            "start_time": "10:00:00",
            "end_time": "12:00:00",
            "slot_type": SlotType.APPOINTMENT.label,
            "slot_size_in_minutes": 30,
            "tokens_per_slot": 10,
        }
        response = self.client.post(self.get_url(), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # check if the response is as per the spec
        response_json_schema = self.get_response_schema()
        self.assert_response_schema(response, response_json_schema)

    def test_update_schedule_exception(self):
        schedule_exception = ScheduleException.objects.create(
            resource=self.schedulable_resource,
            name="test schedule exception",
            is_available=True,
            valid_from="2024-12-09",
            valid_to="2024-12-09",
            start_time=time(hour=10),
            end_time=time(hour=12),
            slot_size_in_minutes=30,
            tokens_per_slot=10,
            slot_type=SlotType.APPOINTMENT,
        )
        data = {
            "name": "test schedule exception 2",
            "slot_size_in_minutes": 45,
        }
        url = self.get_url(schedule_exception.external_id)
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check if the response is as per the spec
        response_json_schema = self.get_response_schema()
        self.assert_response_schema(response, response_json_schema)

        # check if the availability is updated
        schedule_exception.refresh_from_db()
        self.assertEqual(schedule_exception.slot_size_in_minutes, 45)
