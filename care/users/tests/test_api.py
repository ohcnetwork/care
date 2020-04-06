from rest_framework import status
from rest_framework.test import APITestCase

from care.users.models import GENDER_VALUE, User
from config.tests.helper import TestHelper


class TestSuperUser(TestHelper, APITestCase):
    @classmethod
    def setUpTestData(cls):
        """Runs once per class method"""
        # Initalizes the setup data
        cls.setup_data()
        cls.user.is_superuser = True
        cls.user.save()

    def setUp(self):
        """
        Run once before every test
            - login the super user
        """
        self.client.login(**self.user_creds)

    def test_user_creation(self):
        """
        For a superuser account, test
            - for a POST request
                - users can added, status from the response is 201
            - for a GET request
                - object count is 2(1 was created in setUpTestData)
                - username is present in the response
        """
        url = "/api/v1/users/"
        data = self.user_data_client
        data["username"] = "test"
        response = self.client.post(url, data)
        # Test status code
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.get(url)
        res_data_json = response.json()
        # Test object count
        self.assertEqual(res_data_json["count"], 2)
        response = self.client.get(url)
        res_data_json = response.json()
        results = res_data_json["results"]
        # Test presence of username
        self.assertEqual(
            data["username"] in {r["username"] for r in results}, True,
        )

    def test_superuser_can_acess_url_by_location(self):
        """Test super user can acess the url by location"""
        username = self.user_creds["username"]
        response = self.client.get(f"/api/v1/users/{username}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_superuser_can_view(self):
        """Test super user can view all of their profile"""
        username = self.user_creds["username"]
        response = self.client.get(f"/api/v1/users/{username}/")
        res_data_json = response.json()
        res_data_json.pop("id")
        data = self.user_data_client.copy()
        data.pop("password")
        self.assertDictEqual(
            res_data_json,
            {
                **data,
                "gender": GENDER_VALUE.choices.Female.name,
                "is_superuser": True,
                "user_type": User.TYPE_VALUE.choices.Staff.name,
                "first_name": "",
                "last_name": "",
                "local_body": None,
                "district": self.district.id,
                "state": self.state.id,
            },
        )

    def test_superuser_can_modify(self):
        """Test superusers can modify the attributes for other users"""
        username = self.user_creds["username"]
        password = self.user_creds["password"]
        response = self.client.put(
            f"/api/v1/users/{username}/", {**self.user_data_client, "age": 31, "password": password,},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # test the value from api
        self.assertEqual(response.json()["age"], 31)
        # test value at the backend
        self.assertEqual(User.objects.only("age").get(username=username).age, 31)

    def test_superuser_can_delete(self):
        """Test superuser can delete other users"""
        response = self.client.delete(f"/api/v1/users/{self.user_creds['username']}/")
        # test response code
        self.assertEqual(response.status_code, 204)
        # test backend response
        with self.assertRaises(expected_exception=User.DoesNotExist):
            User.objects.get(username=self.user_data["username"])


class TestUser(TestHelper, APITestCase):
    @classmethod
    def setUpTestData(cls):
        """
        Runs once per class method

        Create 2 users
            - 1 will be used to check if they can tinker attributes of the other
        """
        cls.setup_data()
        cls.data_1 = cls.user_data.copy()
        cls.data_1_client = cls.user_data_client.copy()
        cls.user_1 = cls.user
        cls.data_2 = cls.data_1.copy()
        cls.data_2_client = cls.user_data_client.copy()
        cls.data_2["username"] = "user_2"
        cls.data_2_client["username"] = cls.data_2["username"]
        cls.user_2 = User.objects.create_user(**cls.data_2)

    def setUp(self):
        """
        Run once before every test
            - login the super user
        """
        self.client.login(username=self.data_1["username"], password=self.data_1["password"])

    def test_user_can_access_url(self):
        """Test user can access the url by location"""
        username = self.data_1["username"]
        response = self.client.get(f"/api/v1/users/{username}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_can_read_all(self):
        """Test user can read all"""
        response = self.client.get("/api/v1/users/")
        # test response code
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        res_data_json = response.json()
        # test total user count
        self.assertEqual(res_data_json["count"], 2)
        results = res_data_json["results"]
        # test presence of usernames
        self.assertEqual(
            {self.user_1.id, self.user_2.id}, {r["id"] for r in results},
        )

    def test_user_can_modify_themselves(self):
        """Test user can modify the attributes for themselves"""
        password = self.data_1["password"]
        username = self.data_1["username"]
        response = self.client.put(
            f"/api/v1/users/{username}/", {**self.data_1_client, "age": 31, "password": password,},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # test the value from api
        self.assertEqual(response.json()["age"], 31)
        # test value at the backend
        self.assertEqual(User.objects.only("age").get(username=username).age, 31)

    def test_user_can_delete_themselves(self):
        """Test user can't delete themselves"""
        response = self.client.delete(f"/api/v1/users/{self.data_1['username']}/")
        # test response code
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # test backend response
        self.assertIsNotNone(User.objects.get(username=self.data_1["username"]))

    def test_user_can_read_others(self):
        """Test 1 user can read the attributes of the other user"""
        username = self.data_2["username"]
        response = self.client.get(f"/api/v1/users/{username}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_cant_modify_others(self):
        """Test a user can't modify others"""
        username = self.data_2["username"]
        password = self.data_2["password"]
        response = self.client.put(
            f"/api/v1/users/{username}/", {**self.data_2_client, "age": 31, "password": password,},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_can_delete_others(self):
        """Test a user can't delete others"""
        field = "username"
        response = self.client.delete(f"/api/v1/users/{self.data_2[field]}/")
        # test response code
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # test backend response(user_2 still exists)
        self.assertEqual(
            self.data_2[field], User.objects.only(field).get(username=self.data_2[field]).username,
        )
