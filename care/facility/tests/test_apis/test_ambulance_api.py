from typing import Any

from rest_framework import status

from care.facility.models import Ambulance
from care.utils.tests.test_base import TestBase
from config.tests.helper import mock_equal


class TestAmbulance(TestBase):
    """Test Ambulance APIs"""

    @classmethod
    def setUpClass(cls) -> None:
        """
        Initialize the class attributes
        """
        super(TestAmbulance, cls).setUpClass()

    def get_base_url(self) -> str:
        return "/api/v1/ambulance"

    def get_list_representation(self, ambulance) -> dict:
        return {
            "id": ambulance.id,
            "drivers": [self._get_driver_representation(driver) for driver in ambulance.drivers],
            "primary_district_object": self._get_district_object_representation(ambulance.primary_district),
            "secondary_district_object": self._get_district_object_representation(ambulance.secondary_district),
            "third_district_object": self._get_district_object_representation(ambulance.third_district),
            "created_date": mock_equal,
            "modified_date": mock_equal,
            "deleted": ambulance.deleted,
            "vehicle_number": ambulance.vehicle_number,
            "owner_name": ambulance.owner_name,
            "owner_phone_number": ambulance.owner_phone_number,
            "owner_has_smart_phone": ambulance.owner_has_smart_phone,
            "has_oxygen": ambulance.has_oxygen,
            "has_ventilator": ambulance.has_ventilator,
            "has_suction_machine": ambulance.has_suction_machine,
            "has_defibrillator": ambulance.has_defibrillator,
            "insurance_valid_till_year": ambulance.insurance_valid_till_year,
            "ambulance_type": ambulance.ambulance_type,
            "price_per_km": ambulance.price_per_km,
            "has_free_service": ambulance.has_free_service,
            "primary_district": ambulance.primary_district.id,
            "secondary_district": getattr(ambulance.secondary_district, "id", None),
            "third_district": getattr(ambulance.third_district, "id", None),
        }

    def get_detail_representation(self, ambulance: Any = None) -> dict:
        if isinstance(ambulance, dict):
            ambulance = Ambulance(**ambulance)

        return {
            "id": ambulance.id,
            "drivers": [self._get_driver_representation(driver) for driver in ambulance.drivers],
            "primary_district_object": self._get_district_object_representation(ambulance.primary_district),
            "secondary_district_object": self._get_district_object_representation(ambulance.secondary_district),
            "third_district_object": self._get_district_object_representation(ambulance.third_district),
            "created_date": mock_equal,
            "modified_date": mock_equal,
            "deleted": ambulance.deleted,
            "vehicle_number": ambulance.vehicle_number,
            "owner_name": ambulance.owner_name,
            "owner_phone_number": ambulance.owner_phone_number,
            "owner_has_smart_phone": ambulance.owner_has_smart_phone,
            "has_oxygen": ambulance.has_oxygen,
            "has_ventilator": ambulance.has_ventilator,
            "has_suction_machine": ambulance.has_suction_machine,
            "has_defibrillator": ambulance.has_defibrillator,
            "insurance_valid_till_year": ambulance.insurance_valid_till_year,
            "ambulance_type": ambulance.ambulance_type,
            "price_per_km": ambulance.price_per_km,
            "has_free_service": ambulance.has_free_service,
            "primary_district": ambulance.primary_district.id,
            "secondary_district": getattr(ambulance.secondary_district, "id", None),
            "third_district": getattr(ambulance.third_district, "id", None),
        }

    def _get_driver_representation(self, driver: Ambulance.drivers or dict):
        """
        Returns ambulance driver representation for ambulance

        Returns:
            dict
                Representing attributes of the driver

        Params:
            driver: Ambulance.drivers or dict
        """
        if isinstance(driver, dict):
            return {
                "id": mock_equal,
                "name": driver["name"],
                "phone_number": driver["phone_number"],
                "has_smart_phone": driver["has_smart_phone"],
            }
        return {
            "id": driver.id,
            "name": driver.name,
            "phone_number": driver.phone_number,
            "has_smart_phone": driver.has_smart_phone,
        }

    def _get_district_object_representation(self, district):
        """
        Returns district object representation for the ambulance district

        Returns
            dict

        Params
            district: District
                The district object
        """
        if not district:
            return None
        return {
            "id": district.id,
            "name": district.name,
            "state": district.state.id,
        }

    def test_ambulance_api_url_for_unauthenticated_user(self):
        """
        Test whether users can access the url
            - response status code is 403
        """
        # logout the user logged inside TestBase class
        self.client.logout()
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_ambulance_api_url_for_authenticated_user(self):
        """
        Test whether users can access the url
            - test the status code is 200
        """
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ambulance_list(self):
        """
        Test ambulance api gives the expected response for the list request
        """
        response = self.client.get(self.get_url())
        self.assertDictEqual(
            response.json(),
            {
                "count": 1,
                "next": mock_equal,
                "previous": mock_equal,
                "results": [self.get_list_representation(self.ambulance)],
            },
        )

    def test_ambulance_creation(self):
        """
        Test amulance creating
            - verify response code for request is 201
            - verify posted data from
                - api response
                - database
        """
        data = self.ambulance_data
        # ambulance vehicle number has to be unique
        data.update(vehicle_number="AB12CD3456")
        response = self.client.post(self.get_url(action="create"), data)
        breakpoint()
        # test API response
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertDictEqual(response.json(), **self.get_detail_representation(data))

        # test database response
        ambulance = Ambulance.objects.filter(created_by=self.user, primary_district=data["district"]).first()
        self.assertIsNotNone(ambulance)
        self.assertEqual(response.json()["id"], ambulance.id)

    def test_ambulance_retrieval(self):
        """
        Test individual ambulance can be retrieved by their ids
            - verify response code is 200
            - verify response data
        """
        ambulance = self.ambulance

        response = self.client.get(self.get_url(ambulance.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictEqual(response.data, self.get_detail_representation(ambulance))

    def test_ambulance_update(self):
        """
        use PUT method
        """
        pass

    def test_ambulance_partial_update(self):
        """
        use PATCH method
        """
        pass

    def test_ambulance_delete(self):
        """
        Test ambulance deletions
            - verify status code is 204
        """
        ambulance = self.ambulance
        response = self.client.delete(self.get_url(ambulance.id))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_ambulance_add_driver(self):
        """
        Test ambulance users can add drivers to the ambulance
            - verify response code is 201
            - verify the response data with posted data
            - verify the data from the database
        """
        ambulance = self.ambulance
        data = self.get_detail_representation(ambulance)
        driver_1 = {
            "name": "foo",
            "phone_number": "8888888888",
            "has_smart_phone": False,
        }
        driver_2 = {
            "name": "bar",
            "phone_number": "8888888888",
            "has_smart_phone": False,
        }
        data.update(drivers=[driver_1, driver_2])
        # remove created and modified date
        data.pop("created_date", None)
        data.pop("modified_date", None)

        response = self.client.post(self.get_url(ambulance.id, action="add_driver"), data, format="json",)
        breakpoint()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # test data from the API
        self.assertDictEqual(
            response.data.json()["drivers"],
            [{**self._get_driver_representation(driver_1)}, {**self._get_driver_representation(driver_2)},],
        )

        # test model response
        self.refresh_db()
        self.assertEqual(
            ambulance.drivers,
            [{**self._get_driver_representation(driver_1)}, {**self._get_driver_representation(driver_2)},],
        )

    def test_ambulance_remove_driver(self):
        """
        Test ambulance driver deletion
            - verify status code is 204
        """
        ambulance = self.ambulance
        ambulance.created_by = self.user
        ambulance.save()

        response = self.client.delete(self.get_url(ambulance.id, action="remove_driver"))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
