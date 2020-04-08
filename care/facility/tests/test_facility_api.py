import datetime
from typing import Any

from django.contrib.gis.geos import Point
from rest_framework import status

from care.facility.models import Facility, FacilityCapacity
from care.users.models import User
from care.utils.tests.test_base import TestBase
from config.tests.helper import mock_equal


class TestFacility(TestBase):
    """Test Facility APIs"""

    @classmethod
    def setUpClass(cls) -> None:
        super(TestFacility, cls).setUpClass()
        cls.facility_data = {
            "name": "Foo",
            "district": cls.district.id,
            "facility_type": 1,
            "address": f"Address {datetime.datetime.now().timestamp}",
            "location": {"latitude": 49.878248, "longitude": 24.452545},
            "oxygen_capacity": 10,
            "phone_number": "9998887776",
        }

    def get_base_url(self):
        return "/api/v1/facility"

    def get_list_representation(self, facility) -> dict:
        return {
            "id": facility.id,
            "name": facility.name,
            "facility_type": "Educational Inst",
            "address": facility.address,
            "location": {"latitude": facility.location.tuple[1], "longitude": facility.location.tuple[0],},
            "local_body": None,
            "local_body_object": None,
            "district": facility.district.id,
            "district_object": {
                "id": facility.district.id,
                "name": facility.district.name,
                "state": facility.district.state.id,
            },
            "state": facility.district.state.id,
            "state_object": {"id": facility.district.state.id, "name": facility.district.state.name,},
            "oxygen_capacity": facility.oxygen_capacity,
            "phone_number": facility.phone_number,
        }

    def get_detail_representation(self, facility: Any = None) -> dict:
        if isinstance(facility, dict):
            location = facility.pop("location", {})
            district_id = facility.pop("district")
            facility = Facility(
                **facility, district_id=district_id, location=Point(location["longitude"], location["latitude"]),
            )
        return {
            "id": facility.id,
            "name": facility.name,
            "facility_type": "Educational Inst",
            "address": facility.address,
            "location": {"latitude": facility.location.tuple[1], "longitude": facility.location.tuple[0],},
            "local_body": None,
            "local_body_object": None,
            "district": facility.district.id,
            "district_object": {
                "id": facility.district.id,
                "name": facility.district.name,
                "state": facility.district.state.id,
            },
            "state": facility.district.state.id,
            "state_object": {"id": facility.district.state.id, "name": facility.district.state.name,},
            "oxygen_capacity": facility.oxygen_capacity,
            "phone_number": facility.phone_number,
            "created_date": mock_equal,
            "modified_date": mock_equal,
        }

    def test_user_can_create_facility(self):
        """
        Test users can create facility
            - login a normal user
            - verify creation response code is 201
            - verify inserted values
        """
        facility_data = self.facility_data
        response = self.client.post(self.get_url(), facility_data, format="json")

        # test status code
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # test response data
        self.assertDictEqual(
            response.json(),
            {
                **self.get_detail_representation(facility_data),
                "id": mock_equal,
                "modified_date": mock_equal,
                "created_date": mock_equal,
            },
        )

        # Facility exists
        facility = Facility.objects.filter(address=facility_data["address"], created_by=self.user).first()
        self.assertIsNotNone(facility)
        self.assertEqual(response.json()["id"], facility.id)

    def test_inactive_facility_retrieval(self):
        """Test inactive facility are not accessible"""
        facility = self.facility
        facility.created_by = self.user
        facility.is_active = False
        facility.save()
        response = self.client.get(self.get_url(facility.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_active_facility_retrieval(self):
        """Test facility attributes can be retrieved"""
        facility = self.facility
        facility.created_by = self.user
        facility.save()
        response = self.client.get(self.get_url(facility.id), format="json", redirect="follow")

        self.assertDictEqual(
            response.data,
            {**self.get_list_representation(facility), "modified_date": mock_equal, "created_date": mock_equal,},
        )

    def test_facility_update(self):
        """Test facilities attributes can be updated"""
        facility = self.clone_object(self.facility)
        facility.created_by = self.user
        facility.save()

        new_district = self.create_district(self.state)

        response = self.client.put(
            self.get_url(facility.id),
            {
                "name": "Another name",
                "district": new_district.id,
                "facility_type": facility.facility_type,
                "address": facility.address,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_response = self.get_detail_representation(facility)
        expected_response["name"] = "Another name"
        expected_response.update(self.get_district_representation(new_district))
        expected_response.update(self.get_state_representation(new_district.state))
        self.assertDictEqual(
            response.json(), {**expected_response, "modified_date": mock_equal, "created_date": mock_equal,},
        )

        facility.refresh_from_db()
        self.assertEqual(facility.name, "Another name")

    def test_facility_update_doesnt_change_creator(self):
        """Test the updation of facility attribute doesn't change its creator"""
        facility = self.clone_object(self.facility)
        facility.created_by = self.user
        facility.save()
        original_creator = facility.created_by

        self.client.force_login(self.super_user)
        response = self.client.put(self.get_url(facility.id), self.facility_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        facility.refresh_from_db()
        self.assertEqual(facility.created_by, original_creator)

    def test_facility_deletion_for_super(self):
        """
        Test facility deletion can be done
            - response code 204 is returned
            - appropriate exception is raised on subsequent retrieval
        """
        facility = self.clone_object(self.facility)
        user = self.user
        facility.created_by = user
        facility.save()

        user.is_superuser = True
        user.save()

        response = self.client.delete(self.get_url(facility.id))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        with self.assertRaises(Facility.DoesNotExist):
            Facility.objects.get(id=facility.id)

    def test_facility_deletion_failure_for_user(self):
        """
        Test facility deletion can't be done
            - Return a permission error 403
            - Facility exists inside the database
        """
        facility = self.clone_object(self.facility)
        user = self.user
        facility.created_by = user
        facility.save()

        response = self.client.delete(self.get_url(facility.id))
        # Test API response
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # Test database response
        self.assertIsNotNone(Facility.objects.get(id=facility.id))

    def test_facility_list_retrieval_for_user(self):
        """Test retrieval of facility list"""
        facility = self.facility
        facility.created_by = self.user
        facility.save()

        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {**self.get_list_representation(facility), "modified_date": mock_equal, "created_date": mock_equal,}
                ],
            },
        )

    def test_superuser_can_update_ones_facility(self):
        """
        Test superuser can update their facility
            - test status code 201 is returned
        """
        user = self.user
        user.is_superuser = True
        user.save()

        # although this should be put, PUT is weirdly enough not allowed here
        response = self.client.post(self.get_url(), self.get_list_representation(self.facility), format="json",)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class TestFacilityBulkUpdate(TestBase):
    """Test API for bulk updates to facility"""

    def get_base_url(self):
        return "/api/v1/facility/bulk_upsert"

    def get_list_representation(self, facility: Any = None) -> dict:
        if isinstance(facility, dict):
            location = facility.pop("location", {})
            district_id = facility.pop("district")
            facility = Facility(
                **facility, district_id=district_id, location=Point(location["longitude"], location["latitude"]),
            )

        return {
            "name": facility.name,
            "district": facility.district.id,
            "facility_type": 3,
            "address": facility.address,
            "capacity": [{"room_type": 1, "total_capacity": 100, "current_capacity": 48}],
        }

    def get_detail_representation(self):
        # Not really required here
        pass

    def test_facility_bulk_upsert_for_user(self):
        """
        For bulk facility upsert, test for a normal user:
            - permission error is raised
        """
        facility = self.facility

        # capacity = FacilityCapacity.objects.create(
        #     facility=facility, room_type=1, total_capacity=50, current_capacity=0
        # )
        facility.created_by = self.user
        facility.save()

        name = "Another"
        address = "Dasappan's House, Washington Jn, OolaMukk P.O."
        phone_number = "7776665554"
        response = self.client.post(
            self.get_url(),
            data=[
                {
                    "name": facility.name,
                    "district": facility.district.id,
                    "facility_type": 3,
                    "address": facility.address,
                    "capacity": [{"room_type": 1, "total_capacity": 100, "current_capacity": 48,}],
                },
                {
                    "name": name,
                    "district": facility.district.id,
                    "facility_type": 2,
                    "address": address,
                    "phone_number": phone_number,
                    "capacity": [
                        {"room_type": 0, "total_capacity": 350, "current_capacity": 150,},
                        {"room_type": 1, "total_capacity": 200, "current_capacity": 100,},
                    ],
                },
            ],
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_facility_bulk_upsert_for_superuser(self):
        """
        For bulk facility upsert, test for a super user:
            - status code after update
            - test retrived values
        """
        facility = self.facility
        user = self.user

        user.is_superuser = True
        user.save()

        capacity = FacilityCapacity.objects.create(
            facility=facility, room_type=1, total_capacity=50, current_capacity=0
        )
        facility.created_by = self.user
        facility.save()

        name = "Another"
        address = "Dasappan's House, Washington Jn, OolaMukk P.O."
        phone_number = "7776665554"
        response = self.client.post(
            self.get_url(),
            data=[
                {
                    "name": facility.name,
                    "district": facility.district.id,
                    "facility_type": 3,
                    "address": facility.address,
                    "capacity": [{"room_type": 1, "total_capacity": 100, "current_capacity": 48,}],
                },
                {
                    "name": name,
                    "district": facility.district.id,
                    "facility_type": 2,
                    "address": address,
                    "phone_number": phone_number,
                    "capacity": [
                        {"room_type": 0, "total_capacity": 350, "current_capacity": 150,},
                        {"room_type": 1, "total_capacity": 200, "current_capacity": 100,},
                    ],
                },
            ],
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        facility.refresh_from_db()
        self.assertEqual(facility.facility_type, 3)
        capacities = facility.facilitycapacity_set.all()
        self.assertEqual(capacities[0].id, capacity.id)
        self.assertEqual(capacities[0].room_type, 1)
        self.assertEqual(capacities[0].total_capacity, 100)
        self.assertEqual(capacities[0].current_capacity, 48)
        self.assertEqual(len(capacities), 1)

        new_facility = Facility.objects.get(
            created_by=user,
            name=name,
            district=facility.district.id,
            facility_type=2,
            address=address,
            phone_number=phone_number,
        )
        self.assertIsNotNone(new_facility)
        capacities = new_facility.facilitycapacity_set.all()
        self.assertEqual(capacities[0].room_type, 0)
        self.assertEqual(capacities[0].total_capacity, 350)
        self.assertEqual(capacities[0].current_capacity, 150)
        self.assertEqual(capacities[1].room_type, 1)
        self.assertEqual(capacities[1].total_capacity, 200)
        self.assertEqual(capacities[1].current_capacity, 100)
        self.assertEqual(len(capacities), 2)

    def test_unauthenticated_users_cant_access(self):
        """
        Test unauthenticated users can't access
            raise error 403
        """
        # logout the superuser, it's logged in due to the setUp function
        self.client.logout()
        test_facility = TestFacility()
        response = self.client.get(test_facility.get_url(self.facility.id))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_super_user_can_access_url_by_location(self):
        """Test super user can access url by location"""
        user = self.user
        user.is_superuser = True
        user.save()

        test_facility = TestFacility()
        response = self.client.get(test_facility.get_url(self.facility.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_superuser_bulk_facility_data_retrieval(self):
        """Test superusers can retrieve bulk facility data"""
        user = self.user
        user.is_superuser = True
        user.save()

        facility = self.facility

        test_facility = TestFacility()
        response = self.client.get(test_facility.get_url(facility.id), format="json")
        self.assertDictEqual(response.json(), test_facility.get_detail_representation(facility))

    def test_others_cant_update_ones_facility(self):
        """Test facility can't be updated by non-creators"""
        # logout the user, it's logged in due to the setUp function
        self.client.logout()
        data = self.user_data.copy()
        data["username"] = "test"
        User.objects.create_user(**data)
        self.client.login(
            username=data["username"], password=data["password"],
        )
        facility = self.facility
        data = self.user_data
        data["username"] = "random"
        new_user = User.objects.create_user(**data)
        facility.created_by = new_user
        facility.save()
        # although this should be PUT, PUT is weirdly enough not allowed here
        response = self.client.post(self.get_url(), data=self.get_list_representation(facility),)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.json()["detail"], "You do not have permission to perform this action.",
        )
