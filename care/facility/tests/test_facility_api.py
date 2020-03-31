from django.contrib.gis.geos import Point
from rest_framework import status
from rest_framework.test import APITestCase

from care.facility.models import Facility, FacilityCapacity
from care.users.models import User
from care.utils.tests.test_base import TestBase
from config.tests.helper import mock_equal

# flake8: noqa


class TestFacility(TestBase):
    """Test Facility APIs"""

    URL = "/api/v1/facility"

    @classmethod
    def setUpTestData(cls):
        cls.facility_data = {
            "name": "Foo",
            "district": 13,
            "facility_type": 1,
            "address": "8/88, 1st Cross, 1st Main, Boo Layout",
            "location": {"latitude": 49.878248, "longitude": 24.452545},
            "oxygen_capacity": 10,
            "phone_number": "9998887776",
        }

    def test_user_can_create_facility(self):
        """
        Test users can create facility
            - login a normal user
            - verify creation response code is 201
            - verify inserted values
        """
        facility_data = self.facility_data
        response = self.client.post("/api/v1/facility/", facility_data, format="json")

        # test status code
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response.data.pop("id")
        # test response data
        self.assertDictEqual(
            response.data,
            {
                **facility_data,
                "id": mock_equal,
                "facility_type": "Educational Inst",
                "local_govt_body": {
                    "id": mock_equal,
                    "facility": mock_equal,
                    "local_body": None,
                    "district": {"id": 13, "name": "Kannur", "state": 1},
                },
            },
        )

        facility = Facility.objects.get(
            name=facility_data["name"],
            district=facility_data["district"],
            facility_type=facility_data["facility_type"],
            address=facility_data["address"],
            oxygen_capacity=facility_data["oxygen_capacity"],
            phone_number=facility_data["phone_number"],
            created_by=self.user,
        )

        # Facility exists
        assert facility
        facility_loc = facility_data["location"]
        self.assertDictEqual(
            facility_loc, {"latitude": facility_loc["latitude"], "longitude": facility_loc["longitude"],},
        )

    def test_inactive_facility_retrieval(self):
        """Test inactive facility are not accessible"""
        facility = self.facility
        facility.created_by = self.user
        facility.is_active = False
        facility.save()
        response = self.client.get(f"/api/v1/facility/{facility.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_active_facility_retrival(self):
        """Test facility attributes can be retrieved"""
        facility = self.facility
        facility.created_by = self.user
        facility.save()
        response = self.client.get(self.get_url(facility.id), format="json", redirect="follow")
        self.assertDictEqual(
            response.data,
            {
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
                "state_object": {"id": facility.district.state.id, "name": facility.district.state.name},
                "oxygen_capacity": facility.oxygen_capacity,
                "phone_number": facility.phone_number,
            },
        )

    def test_facility_update(self):
        """Test facilities attributes can be updated"""
        facility = self.facility
        facility.created_by = self.user
        facility.save()

        new_district = {"id": 12, "name": "Wayanad"}

        response = self.client.put(
            f"/api/v1/facility/{facility.id}/",
            {
                "name": "Another name",
                "district": new_district["id"],
                "facility_type": facility.facility_type,
                "address": facility.address,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictEqual(
            response.data,
            {
                "id": facility.id,
                "name": "Another name",
                "district": new_district["id"],
                "facility_type": "Educational Inst",
                "address": facility.address,
                "location": {"latitude": facility.location.tuple[1], "longitude": facility.location.tuple[0],},
                "local_govt_body": {
                    "id": mock_equal,
                    "facility": facility.id,
                    "local_body": None,
                    "district": {"id": new_district["id"], "name": new_district["name"], "state": mock_equal,},
                },
                "oxygen_capacity": facility.oxygen_capacity,
                "phone_number": facility.phone_number,
            },
        )
        facility.refresh_from_db()
        self.assertEqual(facility.name, "Another name")

    def test_facility_update_doesnt_change_creator(self):
        """Test the updation of facility attribute doesn't change its creator"""
        facility = self.facility
        facility.created_by = self.user
        facility.save()
        original_creator = facility.created_by

        response = self.client.put(f"/api/v1/facility/{facility.id}/", self.facility_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        facility.refresh_from_db()
        self.assertEqual(facility.created_by, original_creator)

    def test_facility_deletion(self):
        """Test facility deletion can be done and an appropriate error is raised on subsequent retrieval"""
        facility = self.facility
        facility.created_by = self.user
        facility.save()

        response = self.client.delete(f"/api/v1/facility/{facility.id}/",)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        with self.assertRaises(Facility.DoesNotExist):
            Facility.objects.get(id=facility.id)

    def test_facility_list_retrieval(self):
        """Test retrieval of facility list"""
        facility = self.facility
        facility.created_by = self.user
        facility.save()

        response = self.client.get(f"/api/v1/facility/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictEqual(
            response.data,
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": facility.id,
                        "name": facility.name,
                        "district": facility.district,
                        "facility_type": "Educational Inst",
                        "address": facility.address,
                        "location": {"latitude": facility.location.tuple[1], "longitude": facility.location.tuple[0],},
                        "local_govt_body": {
                            "id": mock_equal,
                            "facility": facility.id,
                            "local_body": None,
                            "district": {"id": 13, "name": "Kannur", "state": mock_equal,},
                        },
                        "oxygen_capacity": facility.oxygen_capacity,
                        "phone_number": facility.phone_number,
                    },
                ],
            },
        )


class TestFacilityBulkUpdate(APITestCase):
    """Test API for bulk updates to facility"""

    @classmethod
    def setUpTestData(cls):
        # super(TestFacility, cls).setUpTestData()
        cls.su_data = {
            "user_type": 5,
            "email": "some.email@somedomain.com",
            "phone_number": "5554446667",
            "age": 30,
            "gender": 2,
            "district": 11,
            "username": "superuser_1",
            "password": "bar",
        }
        cls.super_user = User.objects.create_superuser(**cls.su_data)
        cls.user_data = cls.su_data.copy()
        cls.user_data["username"] = "user"
        cls.user = User.objects.create_user(**cls.user_data)
        cls.facility_data = {
            "name": "Foo",
            "district": 13,
            "facility_type": 1,
            "address": "8/88, 1st Cross, 1st Main, Boo Layout",
            "location": {"latitude": 49.878248, "longitude": 24.452545},
            "oxygen_capacity": 10,
            "phone_number": "9998887776",
        }
        # **cls.data is not used because of a issue with the location attribute which requires a Point object
        cls.facility = Facility.objects.create(
            name="Foo",
            district=13,
            facility_type=1,
            address="8/88, 1st Cross, 1st Main, Boo Layout",
            location=Point(24.452545, 49.878248),
            oxygen_capacity=10,
            phone_number="9998887776",
        )

    def setUp(self):
        """This is run before every class method"""
        self.client.login(username=self.su_data["username"], password=self.su_data["password"])

    def test_facility_bulk_upsert(self):
        """
        For bulk facility upsert, test for a normal user:
            - status code after update
            - test retrived values
        """
        facility = self.facility
        user = self.user
        # logout the superuser, it's logged in due to the setUp function
        self.client.logout()
        # login the normal user
        self.client.login(username=self.user_data["username"], password=self.user_data["password"])

        capacity = FacilityCapacity.objects.create(
            facility=facility, room_type=1, total_capacity=50, current_capacity=0
        )
        facility.created_by = user
        facility.save()

        name = "Another"
        address = "Dasappan's House, Washington Jn, OolaMukk P.O."
        phone_number = "7776665554"
        response = self.client.post(
            "/api/v1/facility/bulk_upsert/",
            data=[
                {
                    "name": facility.name,
                    "district": facility.district,
                    "facility_type": 3,
                    "address": facility.address,
                    "capacity": [{"room_type": 1, "total_capacity": 100, "current_capacity": 48,}],
                },
                {
                    "name": name,
                    "district": 1,
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
            created_by=user, name=name, district=1, facility_type=2, address=address, phone_number=phone_number,
        )
        assert new_facility
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
        response = self.client.get(f"/api/v1/facility/{self.facility.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_normal_users_cant_access(self):
        """
        Test normal users can't access
            Error 404 is raised in this case while 403 was raised in the previous one\
            This is weird and not consistent\
            but it is what it is.
        """
        # logout the superuser, it's logged in due to the setUp function
        self.client.logout()
        self.client.login(
            username=self.user_data["username"], password=self.user_data["password"],
        )
        response = self.client.get(f"/api/v1/facility/{self.facility.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_super_user_can_access_url_by_location(self):
        """Test super user can access url by location"""
        response = self.client.get(f"/api/v1/facility/{self.facility.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_superuser_bulk_facility_data_retrieval(self):
        """Test superusers can retrieve bulk facility"""
        user = self.super_user
        facility = self.facility
        response = self.client.get(f"/api/v1/facility/{facility.id}/", format="json")
        self.assertDictEqual(
            response.data,
            {
                "id": facility.id,
                "name": facility.name,
                "district": facility.district,
                "facility_type": "Educational Inst",
                "address": facility.address,
                "location": {"latitude": facility.location.tuple[1], "longitude": facility.location.tuple[0],},
                "local_govt_body": {
                    "id": mock_equal,
                    "facility": facility.id,
                    "local_body": None,
                    "district": {"id": 13, "name": "Kannur", "state": mock_equal},
                },
                "oxygen_capacity": facility.oxygen_capacity,
                "phone_number": facility.phone_number,
            },
        )

    def test_others_cant_update_ones_facility(self):
        """Test facility can't be updated by non-creators"""
        # logout the superuser, it's logged in due to the setUp function
        self.client.logout()
        self.client.login(
            username=self.user_data["username"], password=self.user_data["password"],
        )
        facility = self.facility
        data = self.user_data
        data["username"] = "random"
        new_user = User.objects.create_user(**data)
        facility.created_by = new_user
        facility.save()
        # although this should be put, PUT is weirdly enough not allowed here
        response = self.client.post(
            "/api/v1/facility/bulk_upsert/",
            data=[
                {
                    "name": facility.name,
                    "district": facility.district,
                    "facility_type": 3,
                    "address": facility.address,
                    "capacity": [{"room_type": 1, "total_capacity": 100, "current_capacity": 48}],
                },
            ],
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertRegexpMatches(response.json()["detail"], r"[\w, ()-/]+ is owned by another user")

    def test_superuser_can_update_ones_facility(self):
        """Test superuser can update their facility"""
        facility = self.facility
        # although this should be put, PUT is weirdly enough not allowed here
        response = self.client.post(
            "/api/v1/facility/bulk_upsert/",
            data=[
                {
                    "name": facility.name,
                    "district": facility.district,
                    "facility_type": 3,
                    "address": facility.address,
                    "capacity": [{"room_type": 1, "total_capacity": 100, "current_capacity": 48}],
                },
            ],
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
