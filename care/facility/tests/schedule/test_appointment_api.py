from pydantic import BaseModel, ValidationError
from requests import Response
from rest_framework.test import APITestCase

from care.facility.tests.schedule.setup import ScheduleTestSetup
from care.users.models import User
from care.utils.tests.test_utils import TestUtils


class AppointmentApiTestCase(TestUtils, ScheduleTestSetup, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.setup_schedule()

        cls.second_doctor_user = cls.create_user(
            "second_doctor",
            district=cls.district,
            local_body=cls.local_body,
            user_type=User.TYPE_VALUE_MAP["Doctor"],
            home_facility=cls.facility,
        )

        cls.patient = cls.create_patient(
            district=cls.district,
            facility=cls.facility,
        )

    def get_url(
        self, entry_id=None, action=None, query_params: dict[str, str] | None = None
    ):
        base_url = f"/api/v1/facility/{self.facility.external_id}/appointments/"
        if entry_id is not None:
            base_url += f"{entry_id}/"
        if action is not None:
            base_url += f"{action}/"
        if query_params is not None:
            base_url += f"?{'&'.join([f'{key}={value}' for key, value in query_params.items()])}"
        return base_url

    def get_list_response_schema(self, individual_response_schema):
        class AppointmentListResponseSchema(BaseModel):
            count: int
            next: str | None
            previous: str | None
            results: list[individual_response_schema]

        return AppointmentListResponseSchema

    def assert_response_schema(self, response: Response, schema: BaseModel):
        try:
            schema.validate(response.json())
        except ValidationError as e:
            raise e

    def test_get_available_doctors(self):
        url = self.get_url("available_doctors")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.doctor_user.id)

    def test_get_slots(self):
        url = self.get_url(
            "slots",
            query_params={
                "date_from": "2024-11-18",
                "date_to": "2024-11-18",
                "doctor_username": self.doctor_user.username,
            },
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 4)

        class TokenSlotResponseSchema(BaseModel):
            start_time: str
            end_time: str
            tokens_count: int
            tokens_remaining: int

        self.assert_response_schema(
            response, self.get_list_response_schema(TokenSlotResponseSchema)
        )

    def test_book_appointment(self):
        url = self.get_url()
        data = {
            "patient": self.patient.external_id,
            "doctor_username": self.doctor_user.username,
            "slot_start": "2024-11-18 10:00:00",
            "reason_for_visit": "test reason",
        }

        response = self.client.post(url, data=data, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            str(response.data["patient"].get("id")), str(self.patient.external_id)
        )
        self.assertEqual(
            str(response.data["resource"].get("id")), str(self.doctor_user.external_id)
        )
        self.assertEqual(response.data["reason_for_visit"], "test reason")
