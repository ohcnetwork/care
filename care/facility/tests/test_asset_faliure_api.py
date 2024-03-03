from rest_framework import status
from rest_framework.test import APITestCase

from care.utils.tests.test_utils import TestUtils


class AssetViewSetTestCase(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.asset_location = cls.create_asset_location(cls.facility)
        cls.user = cls.create_user(
            "staff2",
            cls.district,
            home_facility=cls.facility,
            user_type=39,  # state readOnly user
        )
        cls.patient = cls.create_patient(
            cls.district, cls.facility, local_body=cls.local_body
        )

    def setUp(self) -> None:
        super().setUp()

    def test_create_asset_failure(self):
        sample_data = {
            "name": "Test Asset failure",
            "current_location": self.asset_location.pk,
            "asset_type": 50,
            "location": self.asset_location.external_id,
            "warranty_amc_end_of_validity": "2000-04-01",
        }
        self.client.post("/api/v1/asset/", sample_data)
        response = self.client.get("/api/v1/asset/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for i in response.data["results"]:
            self.assertNotEqual(i["name"], "Test Asset failure")
