"""
Test module for Ambulance API
"""

from rest_framework.test import APITestCase

from care.facility.models.ambulance import Ambulance
from care.utils.tests.test_utils import TestUtils


class AmbulanceViewSetTest(TestUtils, APITestCase):
    """
    Test class for Ambulance
    """

    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.user = cls.create_user(
            "user", district=cls.district, local_body=cls.local_body
        )
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.patient = cls.create_patient(
            cls.district, cls.facility, local_body=cls.local_body
        )
        cls.ambulance = cls.create_ambulance(cls.district, cls.user)

    def get_base_url(self) -> str:
        return "/api/v1/ambulance"

    def get_url(self, entry_id=None, action=None):
        """
        Constructs the url for ambulance api
        """
        base_url = f"{self.get_base_url()}/"
        if entry_id is not None:
            base_url += f"{entry_id}/"
        if action is not None:
            base_url += f"{action}/"
        return base_url

    def get_detail_representation(self, obj=None) -> dict:
        return {
            "vehicle_number": obj.vehicle_number,
            "ambulance_type": obj.ambulance_type,
            "owner_name": obj.owner_name,
            "owner_phone_number": obj.owner_phone_number,
            "owner_is_smart_phone": obj.owner_is_smart_phone,
            "deleted": obj.deleted,
            "has_oxygen": obj.has_oxygen,
            "has_ventilator": obj.has_ventilator,
            "has_suction_machine": obj.has_suction_machine,
            "has_defibrillator": obj.has_defibrillator,
            "insurance_valid_till_year": obj.insurance_valid_till_year,
            "has_free_service": obj.has_free_service,
            "primary_district": obj.primary_district.id,
            "primary_district_object": {
                "id": obj.primary_district.id,
                "name": obj.primary_district.name,
                "state": obj.primary_district.state.id,
            },
            "secondary_district": obj.secondary_district,
            "third_district": obj.third_district,
            "secondary_district_object": None,
            "third_district_object": None,
        }

    def get_list_representation(self, obj=None) -> dict:
        return {
            "drivers": list(obj.drivers),
            **self.get_detail_representation(obj),
        }

    def get_create_representation(self) -> dict:
        """
        Returns a representation of a ambulance create request body
        """
        return {
            "vehicle_number": "WW73O2195",
            "owner_name": "string",
            "owner_phone_number": "+918800900466",
            "owner_is_smart_phone": True,
            "has_oxygen": True,
            "has_ventilator": True,
            "has_suction_machine": True,
            "has_defibrillator": True,
            "insurance_valid_till_year": 2020,
            "ambulance_type": 1,
            "primary_district": self.district.id,
        }

    def test_create_ambulance(self):
        """
        Test to create ambulance
        """

        # Test with invalid data
        res = self.client.post(self.get_url(), data=self.get_create_representation())
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["drivers"][0], "This field is required.")

        data = {
            "drivers": [
                {
                    "name": "string",
                    "phone_number": "+919013526849",
                    "is_smart_phone": True,
                }
            ],
        }
        data.update(self.get_create_representation())
        res = self.client.post(self.get_url(), data=data, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json()["non_field_errors"][0],
            "The ambulance must provide a price or be marked as free",
        )

        # Test with valid data
        data.update({"price_per_km": 100})
        res = self.client.post(self.get_url(), data=data, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertTrue(
            Ambulance.objects.filter(vehicle_number=data["vehicle_number"]).exists()
        )

    def test_list_ambulance(self):
        """
        Test to list ambulance
        """
        res = self.client.get(self.get_url())
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["count"], 1)
        expected = self.get_list_representation(self.ambulance)
        actual = res.json()["results"][0]
        self.assertEqual(actual, actual | expected)

    def test_retrieve_ambulance(self):
        """
        Test to retrieve ambulance
        """
        res = self.client.get(f"/api/v1/ambulance/{self.ambulance.id}/")
        self.assertEqual(res.status_code, 200)
        expected = self.get_detail_representation(self.ambulance)
        actual = res.json()
        self.assertEqual(actual, actual | expected)

    def test_update_ambulance(self):
        """
        Test to update ambulance
        """

        res = self.client.patch(
            self.get_url(entry_id=self.ambulance.id),
            data={"vehicle_number": "WW73O2200", "has_free_service": True},
        )
        self.assertEqual(res.status_code, 200)
        self.ambulance.refresh_from_db()
        self.assertEqual(self.ambulance.vehicle_number, "WW73O2200")

    def test_delete_ambulance(self):
        """
        Test to delete ambulance
        """
        res = self.client.delete(self.get_url(entry_id=self.ambulance.id))
        self.assertEqual(res.status_code, 204)
        self.ambulance.refresh_from_db()
        self.assertTrue(self.ambulance.deleted)

    def test_add_driver(self):
        """
        Test to add driver
        """

        res = self.client.post(
            self.get_url(entry_id=self.ambulance.id, action="add_driver"),
            data={
                "name": "string",
                "phone_number": "+919013526800",
                "is_smart_phone": True,
            },
        )

        self.assertEqual(res.status_code, 201)
        self.assertTrue(
            self.ambulance.drivers.filter(phone_number="+919013526800").exists()
        )

    def test_remove_driver(self):
        """
        Test to remove driver
        """

        res = self.client.post(
            self.get_url(entry_id=self.ambulance.id, action="add_driver"),
            data={
                "name": "string",
                "phone_number": "+919013526800",
                "is_smart_phone": True,
            },
        )

        driver_id = res.json()["id"]

        res = self.client.delete(
            self.get_url(
                entry_id=self.ambulance.id,
                action="remove_driver",
            ),
            data={"driver_id": driver_id},
        )
        self.assertEqual(res.status_code, 204)
        self.assertFalse(self.ambulance.drivers.exists())
