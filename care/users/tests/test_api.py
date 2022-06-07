from rest_framework import status

from care.users.models import User, GENDER_CHOICES
from care.utils.tests.test_base import TestBase


class TestSuperUser(TestBase):
    def setUp(self):
        """
        Run once before every test
            - login the super user
        """
        self.client.force_authenticate(self.super_user)

    def get_detail_representation(self, obj=None) -> dict:
        return {
            "username": obj.username,
            "first_name": obj.first_name,
            "last_name": obj.last_name,
            "email": obj.email,
            "user_type": obj.get_user_type_display(),
            "created_by": obj.created_by,
            "phone_number": obj.phone_number,
            "alt_phone_number": obj.alt_phone_number,
            "age": obj.age,
            "gender": GENDER_CHOICES[obj.gender - 1][1],
            "is_superuser": obj.is_superuser,
            "verified": obj.verified,
            "pf_endpoint": obj.pf_endpoint,
            "pf_p256dh": obj.pf_p256dh,
            "pf_auth": obj.pf_auth,
            **self.get_local_body_district_state_representation(obj),
        }

    def test_superuser_can_access_url_by_location(self):
        """Test super user can access the url by location"""
        response = self.client.get(f"/api/v1/users/{self.user.username}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_superuser_can_view(self):
        """Test super user can view all of their profile"""
        response = self.client.get(f"/api/v1/users/{self.user.username}/")
        res_data_json = response.json()
        res_data_json.pop("id")

        data = self.user_data.copy()
        data.pop("password")
        self.assertDictEqual(
            res_data_json, self.get_detail_representation(self.user),
        )

    def test_superuser_can_modify(self):
        """Test superusers can modify the attributes for other users"""
        username = self.user.username
        password = "new_password"

        data = self.user_data.copy()
        data["district"] = data["district"].id
        data["state"] = data["state"].id

        response = self.client.patch(f"/api/v1/users/{username}/", {"age": 31},)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # test the value from api
        self.assertEqual(response.json()["age"], 31)
        # test value at the backend
        self.assertEqual(User.objects.get(username=username).age, 31)

    def test_superuser_can_delete(self):
        """Test superuser can delete other users"""
        response = self.client.delete(f"/api/v1/users/{self.user.username}/")
        # test response code
        self.assertEqual(response.status_code, 204)
        # test backend response
        with self.assertRaises(expected_exception=User.DoesNotExist):
            User.objects.get(username=self.user_data["username"], is_active=True, deleted=False)


class TestUser(TestBase):
    def get_detail_representation(self, obj=None) -> dict:
        return {
            "username": obj.username,
            "user_type": obj.get_user_type_display(),
            "is_superuser": obj.is_superuser,
            "gender": obj.get_gender_display(),
            "email": obj.email,
            "phone_number": obj.phone_number,
            "first_name": obj.first_name,
            "last_name": obj.last_name,
            "age": obj.age,
            **self.get_local_body_district_state_representation(obj),
        }

    @classmethod
    def setUpClass(cls) -> None:
        """
        Runs once per class method

        Create 2 users
            - 1 will be used to check if they can tinker attributes of the other
        """
        super(TestUser, cls).setUpClass()
        cls.data_2 = cls.get_user_data()
        cls.data_2.update({"username": "user_2", "password": "password"})
        cls.user_2 = cls.create_user(district=cls.district, username="user_2")

    def setUp(self):
        """
        Run once before every test
            - login the super user
        """
        self.client.force_login(self.user)

    def test_user_can_access_url(self):
        """Test user can access the url by location"""
        username = self.user.username
        response = self.client.get(f"/api/v1/users/{username}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_can_read_all(self):
        """Test user can read all"""
        response = self.client.get("/api/v1/users/")
        # test response code
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        res_data_json = response.json()
        # test total user count
        self.assertEqual(res_data_json["count"], 2)  # 2 existing, plus the new one
        results = res_data_json["results"]
        # test presence of usernames
        self.assertIn(self.user.id, {r["id"] for r in results})
        self.assertIn(self.user_2.id, {r["id"] for r in results})

    def test_user_can_modify_themselves(self):
        """Test user can modify the attributes for themselves"""
        password = "new_password"
        username = self.user.username
        response = self.client.patch(f"/api/v1/users/{username}/", {"age": 31, "password": password, },)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # test the value from api
        self.assertEqual(response.json()["age"], 31)
        # test value at the backend
        self.assertEqual(User.objects.get(username=username).age, 31)

    def test_user_cannot_read_others(self):
        """Test 1 user can read the attributes of the other user"""
        username = self.data_2["username"]
        response = self.client.get(f"/api/v1/users/{username}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_cannot_modify_others(self):
        """Test a user can't modify others"""
        username = self.data_2["username"]
        password = self.data_2["password"]
        response = self.client.patch(f"/api/v1/users/{username}/", {"age": 31, "password": password, },)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_cannot_delete_others(self):
        """Test a user can't delete others"""
        field = "username"
        response = self.client.delete(f"/api/v1/users/{self.data_2[field]}/")
        # test response code
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # test backend response(user_2 still exists)
        self.assertEqual(
            self.data_2[field], User.objects.get(username=self.data_2[field]).username,
        )
