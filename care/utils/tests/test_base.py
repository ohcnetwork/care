import datetime

from django.contrib.gis.geos import Point
from rest_framework import status
from rest_framework.test import APITestCase

from care.facility.models import Facility, User
from care.users.models import District, State


class TestBase(APITestCase):
    URL = ""

    @classmethod
    def create_user(cls, district: District, username: str = "user", **kwargs):
        username = kwargs.get("username", username)
        data = {
            "email": f"{username}@somedomain.com",
            "phone_number": "5554446667",
            "age": 30,
            "gender": 2,
            "username": username,
            "password": "bar",
            "district": district,
            "user_type": User.TYPE_VALUE_MAP["Staff"],
        }
        data.update(kwargs)
        return User.objects.create_user(**data)

    @classmethod
    def create_super_user(cls, district: District, username: str = "superuser"):
        user = cls.create_user(district=district, username=username, user_type=User.TYPE_VALUE_MAP["DistrictAdmin"])
        user.is_superuser = True
        user.save()
        return user

    @classmethod
    def create_district(cls, state: State):
        return District.objects.create(state=state, name=f"District{datetime.datetime.now().timestamp()}")

    @classmethod
    def create_state(cls):
        return State.objects.create(name=f"State{datetime.datetime.now().timestamp()}")

    @classmethod
    def create_facility(cls, district: District):
        return Facility.objects.create(
            name="Foo",
            district=district,
            facility_type=1,
            address="8/88, 1st Cross, 1st Main, Boo Layout",
            location=Point(24.452545, 49.878248),
            oxygen_capacity=10,
            phone_number="9998887776",
        )

    @classmethod
    def setUpClass(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.user = cls.create_user(cls.district)
        cls.super_user = cls.create_super_user(district=cls.district)
        cls.facility = cls.create_facility(cls.district)

    def setUp(self) -> None:
        self.client.force_login(self.user)

    def get_url(self, id=None, action=None):
        url = self.URL
        if id is not None:
            url = f"{url}/{id}"
        if action is not None:
            url = f"{url}/{action}"
        return f"{url}/"

    def test_login_required(self):
        """Test unlogged unusers are thrown an error 403"""
        # Terminate the user session since user is logged in inside the setUp function
        self.client.logout()
        response = self.client.post(self.get_url(), {},)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
