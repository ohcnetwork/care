from typing import Any

from rest_framework import status

from care.facility.models import Ambulance, AmbulanceDriver, District
from care.utils.tests.test_base import TestBase
from config.tests.helper import mock_equal


class TestAmbulance(TestBase):
    """Test ambulance APIs"""

    @classmethod
    def setUpClass(cls):
        """
        Runs once per class
            - Initialize the attributes useful for class methods
        """
        super(TestAmbulance, cls).setUpClass()

    def get_base_url(self):
        return "/api/v1/ambulance"

    def get_detail_representation(self, ambulance: Any):

        if isinstance(ambulance, dict):
            this_ambulance = ambulance.copy()
            this_ambulance.pop("drivers", [])
            this_ambulance_data = this_ambulance.copy()
            this_ambulance_data["primary_district"] = self.get_district_object(this_ambulance_data["primary_district"])
            this_ambulance_data["secondary_district"] = self.get_district_object(
                this_ambulance_data["secondary_district"]
            )
            this_ambulance_data["third_district"] = self.get_district_object(this_ambulance_data["third_district"])
            ambulance = Ambulance(**this_ambulance_data)

        return {
            "id": mock_equal,
            "drivers": mock_equal,
            "primary_district_object": self.format_district(ambulance.primary_district),
            "secondary_district_object": self.format_district(ambulance.secondary_district),
            "third_district_object": self.format_district(ambulance.third_district),
            "created_date": mock_equal,
            "modified_date": mock_equal,
            "deleted": ambulance.deleted,
            "vehicle_number": ambulance.vehicle_number,
            "owner_name": ambulance.owner_name,
            "owner_phone_number": ambulance.owner_phone_number,
            "owner_is_smart_phone": ambulance.owner_is_smart_phone,
            "has_oxygen": ambulance.has_oxygen,
            "has_ventilator": ambulance.has_ventilator,
            "has_suction_machine": ambulance.has_suction_machine,
            "has_defibrillator": ambulance.has_defibrillator,
            "insurance_valid_till_year": ambulance.insurance_valid_till_year,
            "ambulance_type": ambulance.ambulance_type,
            "price_per_km": ambulance.price_per_km,
            "has_free_service": ambulance.has_free_service,
            "primary_district": ambulance.primary_district.id,
            "secondary_district": ambulance.secondary_district.id,
            "third_district": ambulance.third_district.id,
        }

    def get_district_object(self, dist_obj_id):
        return District.objects.get(id=dist_obj_id)

    def format_district(self, district):
        return {"id": district.id, "name": district.name, "state": district.state.id}

    def test_login_required(self):
        """Test permission error is raised for unauthorised access"""
        # logout the user logged in during setUp function
        self.client.logout()
        response = self.client.post(self.get_url(), {},)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_ambulance_creation(self):
        """
        For new ambulance can be creation, test
            - status code is 201
            - ambulance data is returned from response
            - ambulance is created on the backend
        """
        ambulance_data = self.ambulance_data.copy()
        ambulance_data["vehicle_number"] = "KL11AB1234"
        ambulance_data["drivers"] = [{"name": "Arun", "phone_number": "9446380896", "is_smart_phone": True}]
        unverified_user = self.clone_object(self.user, save=False)
        unverified_user.username = "unverified_user_test_ambulance_creation"
        unverified_user.verified = False
        unverified_user.save()

        self.client.force_authenticate(unverified_user)
        response = self.client.post(self.get_url("create"), ambulance_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)  # Any user can create

        ambulance_data["vehicle_number"] = "KL11AB4321"
        ambulance_data["drivers"] = [{"name": "Arjun", "phone_number": "9446380897", "is_smart_phone": True}]
        self.client.force_authenticate(self.user)
        response = self.client.post(self.get_url("create"), ambulance_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertDictEqual(response.json(), self.get_detail_representation(ambulance_data))

        ambulance = Ambulance.objects.filter(vehicle_number=ambulance_data["vehicle_number"]).first()
        self.assertIsNotNone(ambulance)
        self.assertIsNotNone(ambulance.drivers.all().count(), len(ambulance_data["drivers"]))

        self.assertEqual(ambulance.owner_phone_number, ambulance_data["owner_phone_number"])

    def test_ambulance_retrieval(self):
        """
        Test users can retrieve ambulances created by them
            - test status code
            - test response.json()
        """
        ambulance = self.ambulance
        ambulance.created_by = self.user
        ambulance.save()
        response = self.client.get(self.get_url(self.ambulance.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictEqual(response.json(), self.get_detail_representation(ambulance))

    def test_ambulance_patch(self):
        """
        Test user can update their ambulance details
            - test status code
            - test response.json()
            - test data from database
        """
        ambulance = self.clone_object(self.ambulance, save=False)
        ambulance.created_by = self.user
        ambulance.vehicle_number = "KL10AB1234"
        ambulance.save()

        has_free_service = False
        self.client.force_authenticate(user=None)
        response = self.client.patch(
            self.get_url(ambulance.id), {"has_free_service": has_free_service, "price_per_km": "10.00"}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)  # only for authenticated users

        self.client.force_authenticate(self.user)
        response = self.client.patch(
            self.get_url(ambulance.id), {"has_free_service": has_free_service, "price_per_km": "10.00"}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)  # only for verified users

        ambulance.refresh_from_db()
        self.assertEqual(ambulance.has_free_service, has_free_service)

    def test_ambulance_put(self):
        """
        Test user can update their ambulance details
            - test status code
            - test response.json()
            - test data from database
        """
        ambulance = self.clone_object(self.ambulance, save=False)
        ambulance.created_by = self.user
        ambulance.vehicle_number = "KL09AB1234"
        ambulance.save()
        ambulance.refresh_from_db()

        has_free_service = False
        data = self.get_detail_representation(ambulance)
        data.update(
            {
                "has_free_service": has_free_service,
                "price_per_km": "10.00",
                "drivers": [{"name": "Aladin", "phone_number": "9442380896", "is_smart_phone": True}],
            }
        )
        keys_to_pop = [key for key, value in data.items() if value is mock_equal]
        for key in keys_to_pop:
            data.pop(key)
        response = self.client.put(self.get_url(ambulance.id), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)  # only for verified users

        ambulance.refresh_from_db()
        self.assertEqual(ambulance.has_free_service, has_free_service)
        self.assertEquals(str(ambulance.price_per_km), "10.00")

    def test_user_can_delete_ambulance(self):
        """
        Test users can delete ambulance
            - test permission error
        """
        user = self.clone_object(self.user, save=False)
        user.username = "username__test_user_can_delete_ambulance"
        user.save()

        ambulance = self.clone_object(self.ambulance, save=False)
        ambulance.vehicle_number = "KL14AB1234"
        ambulance.created_by = self.user
        ambulance.save()
        ambulance.ambulancedriver_set.add(
            AmbulanceDriver(**{"name": "Aladin", "phone_number": "9442380896", "is_smart_phone": True}), bulk=False,
        )
        ambulance.save()

        self.client.force_authenticate(user=None)
        response = self.client.delete(
            self.get_url(ambulance.id), {"driver_id": ambulance.drivers.first().id}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.user)
        response = self.client.delete(
            self.get_url(ambulance.id), {"driver_id": ambulance.drivers.first().id}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_superuser_can_delete_ambulance(self):
        """
        Test superuser can delete ambulance
            - test status code
            - test data from database
        """
        ambulance = self.ambulance
        ambulance.ambulancedriver_set.add(
            AmbulanceDriver(**{"name": "Aladin", "phone_number": "9442380896", "is_smart_phone": True}), bulk=False,
        )
        user = self.user
        user.is_superuser = True
        user.save()
        ambulance.created_by = user

        ambulance.save()
        response = self.client.delete(
            self.get_url(ambulance.id), {"driver_id": ambulance.drivers.first().id}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        with self.assertRaises(Ambulance.DoesNotExist):
            Ambulance.objects.get(id=ambulance.id)

    def test_ambulance_list_is_accessible_by_url(self):
        """Test user can retreive their ambulance list by the url"""
        ambulance = self.ambulance

        ambulance.created_by = self.user
        ambulance.save()
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_superuser_access(self):
        """
        Test superuser can retrieve ambulance details
            - test status code
            - test response.json()
        """
        ambulance = self.ambulance
        user = self.user
        user.is_superuser = True
        user.save()
        response = self.client.get(self.get_url(entry_id=ambulance.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictEqual(response.json(), self.get_detail_representation(ambulance))

    def test_add_driver(self):
        ambulance = self.clone_object(self.ambulance, save=False)
        ambulance.vehicle_number = "KL15AB1234"
        ambulance.save()

        self.client.force_authenticate(self.user)
        # check for invalid phone number
        response = self.client.post(
            self.get_url(ambulance.id, "add_driver"),
            {"name": "Venkit", "phone_number": "1234", "is_smart_phone": True},
            format="json",
        )
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

        # check for invalid phone number
        response = self.client.post(
            self.get_url(ambulance.id, "add_driver"),
            {"name": "Venkit", "phone_number": "9887481886", "is_smart_phone": True},
            format="json",
        )
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

    def test_remove_driver(self):
        ambulance = self.clone_object(self.ambulance, save=False)
        ambulance.created_by = self.user
        ambulance.vehicle_number = "KL16AB1234"
        ambulance.save()
        ambulance.ambulancedriver_set.add(
            AmbulanceDriver(**{"name": "Abi", "phone_number": "9442380895", "is_smart_phone": True}), bulk=False,
        )
        ambulance.save()
        ambulance.refresh_from_db()

        driver_id = ambulance.ambulancedriver_set.first().id

        # remove without driver id
        response = self.client.delete(self.get_url(ambulance.id, "remove_driver"))
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

        # remove with driver id
        response = self.client.delete(self.get_url(ambulance.id, "remove_driver"), {"driver_id": driver_id})
        self.assertEquals(response.status_code, status.HTTP_204_NO_CONTENT)
