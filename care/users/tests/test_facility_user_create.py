from rest_framework import status

from care.facility.models import FacilityUser
from care.users.models import User
from care.utils.tests.test_base import TestBase
from config.tests.helper import mock_equal


class TestFacilityUserApi(TestBase):
    def get_base_url(self):
        return "/api/v1/users/add_user"

    def get_list_representation(self, obj) -> dict:
        raise NotImplementedError

    def get_detail_representation(self, obj: User = None) -> dict:
        return {
            "id": obj.id,
            "user_type": obj.get_user_type_display(),
            "gender": obj.get_gender_display(),
            "password": mock_equal,
            "username": obj.username,
            "first_name": obj.first_name,
            "last_name": obj.last_name,
            "email": obj.email,
            "phone_number": obj.phone_number,
            "age": obj.age,
            "local_body": getattr(obj.local_body, "id", None),
            "district": getattr(obj.district, "id", None),
            "state": getattr(obj.state, "id", None),
            "skill": obj.skill,
        }

    def get_new_user_data(self):
        return {
            "username": "roopak",
            "user_type": "Staff",
            "phone_number": "+917795937091",
            "gender": "Male",
            "age": 28,
            "first_name": "Roopak",
            "last_name": "A N",
            "email": "anroopak@gmail.com",
            "district": self.district.id,
            "verified": True,
            "facilities": [self.facility.external_id],
        }

    def test_create_facility_user__should_succeed__when_same_level(self):
        data = self.get_new_user_data().copy()

        response = self.client.post(self.get_url(), data=data, format="json")
        # Test Creation
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        user_id = response.json()["id"]
        user = User.objects.filter(id=user_id).first()
        self.assertIsNotNone(user)
        self.assertDictEqual(response.json(), self.get_detail_representation(user))

        # Test for login
        password = response.json()["password"]
        self.client.login(username=data["username"], password=password)
        response = self.client.post(
            f"/api/v1/auth/login/", data={"username": data["username"], "password": password}, format="json"
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        # Test if user is added to the facility
        self.assertIn(user, self.facility.users.all())
        response = self.client.get(f"/api/v1/facility/{self.facility.external_id}/")
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        self.assertEquals(
            FacilityUser.objects.filter(facility=self.facility, user=user, created_by=self.user).count(), 1
        )

    def test_create_facility_user__should_succeed__when_lower_level(self):
        data = self.get_new_user_data().copy()
        data.update({"user_type": "Doctor"})

        response = self.client.post(self.get_url(), data=data, format="json")
        # Test Creation
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        user_id = response.json()["id"]
        user = User.objects.filter(id=user_id).first()
        self.assertIsNotNone(user)
        self.assertDictEqual(response.json(), self.get_detail_representation(user))

        # Test for login
        password = response.json()["password"]
        self.client.login(username=data["username"], password=password)
        response = self.client.post(
            f"/api/v1/auth/login/", data={"username": data["username"], "password": password}, format="json"
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        # Test if user is added to the facility
        self.assertIn(user, self.facility.users.all())
        response = self.client.get(f"/api/v1/facility/{self.facility.external_id}/")
        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_create_facility_user__should_fail__when_higher_level(self):
        data = self.get_new_user_data().copy()
        data.update({"user_type": "DistrictAdmin"})

        response = self.client.post(self.get_url(), data=data, format="json")
        # Test Creation
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_facility_user__should_fail__when_different_location(self):
        new_district = self.clone_object(self.district)
        data = self.get_new_user_data().copy()
        data.update({"district": new_district.id})

        response = self.client.post(self.get_url(), data=data, format="json")
        # Test Creation
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
