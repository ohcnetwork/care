from enum import Enum

from rest_framework import status
from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.tokens import RefreshToken

from care.facility.models import FACILITY_TYPES
from care.facility.models.facility import FacilityUser
from care.facility.tests.mixins import TestClassMixin
from care.users.models import User
from care.utils.tests.test_base import TestBase


class ExpectedListUserKeys(Enum):
    id = "id"
    last_login = "last_login"
    first_name = "first_name"
    last_name = "last_name"
    home_facility = "home_facility"
    username = "username"
    home_facility_object = "home_facility_object"
    user_type = "user_type"


class ExpectedHomeObjectKeys(Enum):
    id = "id"
    name = "name"


class ExpectedDistrictObjectKeys(Enum):
    id = "id"
    name = "name"
    state = "state"


class StateObjectKeys(Enum):
    id = "id"
    name = "name"


class ExpectedRetrieveUserKeys(Enum):
    id = "id"
    username = "username"
    first_name = "first_name"
    last_name = "last_name"
    email = "email"
    user_type = "user_type"
    doctor_qualification = "doctor_qualification"
    doctor_experience_commenced_on = "doctor_experience_commenced_on"
    doctor_medical_council_registration = "doctor_medical_council_registration"
    created_by = "created_by"
    home_facility = "home_facility"
    weekly_working_hours = "weekly_working_hours"
    local_body = "local_body"
    district = "district"
    state = "state"
    phone_number = "phone_number"
    alt_phone_number = "alt_phone_number"
    gender = "gender"
    age = "age"
    is_superuser = "is_superuser"
    verified = "verified"
    home_facility_object = "home_facility_object"
    local_body_object = "local_body_object"
    district_object = "district_object"
    state_object = "state_object"
    pf_endpoint = "pf_endpoint"
    pf_p256dh = "pf_p256dh"
    pf_auth = "pf_auth"


class UserViewSetTestCase(TestBase, TestClassMixin):
    current_district = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.factory = APIRequestFactory()
        state = cls.create_state()
        district = cls.create_district(state=state)
        cls.current_district = district
        cls.user = cls.create_user(district=district, username="test user")
        cls.user.pf_endpoint = "test_endpoint"
        cls.user.pf_p256dh = "test_p256dh"
        cls.user.pf_auth = "test_auth"
        cls.user.save(update_fields=["pf_endpoint", "pf_p256dh", "pf_auth"])
        cls.superuser = cls.create_user(district=district, username="test superuser")
        cls.superuser.is_superuser = True
        cls.superuser.save(update_fields=["is_superuser"])
        cls.state_admin = cls.create_user(
            district=district,
            username="test state admin",
            user_type=User.TYPE_VALUE_MAP["StateAdmin"],
        )

    def get_access_token(self, user):
        return RefreshToken.for_user(user).access_token

    def setUp(self):
        # Refresh token to header
        refresh_token = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh_token.access_token}"
        )

    def test_list_user(self):
        response = self.client.get("/api/v1/users/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.json()["results"], list)

        # Ensure only necessary data is being sent and no extra data
        expected_keys = [key.value for key in ExpectedListUserKeys]

        data = response.json()["results"][0]

        self.assertCountEqual(data.keys(), expected_keys)

        expected_home_object_keys = [key.value for key in ExpectedHomeObjectKeys]

        if data["home_facility_object"]:
            self.assertCountEqual(
                data["home_facility_object"].keys(), expected_home_object_keys
            )

    def test_retrieve_user(self):
        response = self.client.get(f"/api/v1/users/{self.user.username}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Ensure only necessary data is being sent and no extra data
        expected_keys = [key.value for key in ExpectedRetrieveUserKeys]

        data = response.json()

        self.assertCountEqual(data.keys(), expected_keys)

        expected_home_object_keys = [key.value for key in ExpectedHomeObjectKeys]

        if data["home_facility_object"]:
            self.assertCountEqual(
                data["home_facility_object"].keys(), expected_home_object_keys
            )

        self.assertCountEqual(
            data["district_object"].keys(),
            [key.value for key in ExpectedDistrictObjectKeys],
        )

        self.assertCountEqual(
            data["state_object"].keys(), [key.value for key in StateObjectKeys]
        )

    def test_pnconfig_get(self):
        response = self.client.get(f"/api/v1/users/{self.user.username}/pnconfig/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["pf_endpoint"], "test_endpoint")
        self.assertEqual(response.data["pf_p256dh"], "test_p256dh")
        self.assertEqual(response.data["pf_auth"], "test_auth")

    def test_pnconfig_patch(self):
        url = f"/api/v1/users/{self.user.username}/pnconfig/"
        data = {
            "pf_endpoint": "new_endpoint",
            "pf_p256dh": "new_p256dh",
            "pf_auth": "new_auth",
        }
        response = self.client.patch(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.pf_endpoint, "new_endpoint")
        self.assertEqual(self.user.pf_p256dh, "new_p256dh")
        self.assertEqual(self.user.pf_auth, "new_auth")

    def test_check_availability_available(self):
        url = f"/api/v1/users/{self.user.username}/check_availability/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

        url = "/api/v1/users/unavailable-username/check_availability/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_facility_user(self):
        dummy_facility = self.create_facility(
            district=self.district, name="dummyfacility", user=self.user
        )
        dummy_user = self.create_user(
            district=self.district,
            username="dummyuser",
            created_by=self.user,
            user_type=User.TYPE_VALUE_MAP["Volunteer"],
        )
        FacilityUser.objects.create(
            facility=dummy_facility, user=dummy_user, created_by=self.user
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.get_access_token(self.superuser)}"
        )
        response = self.client.delete(
            f"/api/v1/users/{dummy_user.username}/delete_facility/"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), {"facility": "required"})

        data = {"facility": "e8fdaf3b-cefc-47f8-a6a8-e645462a1a24"}
        response = self.client.delete(
            f"/api/v1/users/{dummy_user.username}/delete_facility/", data=data
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), {"facility": "Does not Exist"})

        data = {"facility": str(dummy_facility.external_id)}
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.get_access_token(dummy_user)}"
        )
        response = self.client.delete(
            f"/api/v1/users/{self.user.username}/delete_facility/", data=data
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(), {"facility": "cannot Access Higher Level User"}
        )

        requesting_user = self.create_user(
            district=self.district,
            username="requesting user",
            user_type=User.TYPE_VALUE_MAP["Staff"],
        )
        user = self.create_user(
            district=self.district,
            username="testuser1",
            user_type=User.TYPE_VALUE_MAP["Volunteer"],
        )
        FacilityUser.objects.create(
            facility=dummy_facility, user=user, created_by=requesting_user
        )

        # set up request
        url = f"/api/v1/users/{user.username}/delete_facility/"
        data = {"facility": str(dummy_facility.external_id)}
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.get_access_token(requesting_user)}"
        )

        # test requesting user does not have facility permission
        response = self.client.delete(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), {"facility": "Facility Access not Present"})

        # give requesting user facility permission
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.get_access_token(self.superuser)}"
        )

        dummy_user2 = self.create_user(
            district=self.district,
            username="dummyuser2",
            created_by=self.user,
            user_type=User.TYPE_VALUE_MAP["Volunteer"],
        )
        url = f"/api/v1/users/{dummy_user2.username}/delete_facility/"
        # test user does not have facility permission
        response = self.client.delete(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"facility": "Intended User Does not have permission to this facility"},
        )

        url = f"/api/v1/users/{requesting_user.username}/delete_facility/"
        requesting_user.user_type = User.TYPE_VALUE_MAP["StateLabAdmin"]
        requesting_user.state = self.state
        requesting_user.home_facility = dummy_facility
        requesting_user.save(update_fields=["home_facility", "user_type", "state"])
        requesting_user.refresh_from_db()
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.get_access_token(requesting_user)}"
        )
        response = self.client.delete(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(), {"facility": "Cannot Delete User's Home Facility"}
        )

        # set user's home facility to a different facility
        requesting_user.home_facility = None
        requesting_user.save()

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.get_access_token(self.state_admin)}"
        )
        # test successful deletion of facility user
        response = self.client.delete(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_get_current_user(self):
        response = self.client.get("/api/v1/users/getcurrentuser/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["username"], self.user.username)

    # TODO: Giving This querydict is immutable error
    # def test_add_user(self):
    #     # set up request
    #     url = "/api/v1/users/add_user/"
    #     data = {
    #         "user_type": "Volunteer",
    #         "gender": 1,
    #         "username": "new user",
    #         "phone_number": "1234567890",
    #         "age": 25,
    #         "district": self.current_district
    #     }
    #     self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.get_access_token(self.state_admin)}")

    #     # test add user
    #     response = self.client.post(url, data=data)
    #     self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    #     # check if user was created
    #     new_user = User.objects.filter(username=data["username"]).first()
    #     self.assertIsNotNone(new_user)
    #     self.assertEqual(new_user.user_type, data["user_type"])
    #     self.assertEqual(new_user.gender, data["gender"])
    #     self.assertEqual(new_user.phone_number, data["phone_number"])
    #     self.assertEqual(new_user.age, data["age"])

    def test_delete_user(self):
        dummy_user1 = self.create_user(username="dummyuser1")
        dummy_user2 = self.create_user(
            state=self.state_admin.state,
            district=self.state_admin.district,
            username="dummyuser2",
            user_type=User.TYPE_VALUE_MAP["StateLabAdmin"],
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.get_access_token(self.superuser)}"
        )
        response = self.client.delete(f"/api/v1/users/{dummy_user1.username}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        dummy_user1.refresh_from_db()
        self.assertEqual(dummy_user1.is_active, False)

        # Ensure user is deleted
        response = self.client.get(f"/api/v1/users/{dummy_user1.username}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.get_access_token(self.state_admin)}"
        )
        response = self.client.delete(f"/api/v1/users/{dummy_user2.username}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        dummy_user2.refresh_from_db()
        self.assertEqual(dummy_user2.is_active, False)

        # Ensure user is deleted
        response = self.client.get(f"/api/v1/users/{dummy_user2.username}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_add_facility_missing_facility(self):
        response = self.client.put(f"/api/v1/users/{self.user.username}/add_facility/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"facility": "required"})

    def test_add_facility_non_existent_facility(self):
        response = self.client.put(
            f"/api/v1/users/{self.user.username}/add_facility/",
            data={"facility": "3df87649-e511-4e23-b6b1-182812d8fe44"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"facility": "Does not Exist"})

    def test_add_facility_no_permission_elevation(self):
        facility = self.create_facility(district=self.district, name="Test Facility 4")
        response = self.client.put(
            f"/api/v1/users/{self.state_admin.username}/add_facility/",
            data={"facility": facility.external_id},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"facility": "cannot Access Higher Level User"})

    def test_add_facility_already_exists(self):
        facility = self.create_facility(district=self.district, name="Test Facility 1")
        response = self.client.put(
            f"/api/v1/users/{self.user.username}/add_facility/",
            data={"facility": facility.external_id},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data, {"facility": "User Already has permission to this facility"}
        )

    def test_add_facility_success(self):
        facility = self.create_facility(district=self.district, name="Test Facility 1")
        user2 = self.create_user(district=self.district, username="testuser2")
        response = self.client.put(
            f"/api/v1/users/{user2.username}/add_facility/",
            data={"facility": facility.external_id},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_get_facilities(self):
        user1 = self.create_user(
            district=self.district,
            username="testuser1",
            user_type=User.TYPE_VALUE_MAP["StateAdmin"],
        )
        facility1 = self.create_facility(
            name="Test Facility Unique 1",
            facility_type=FACILITY_TYPES[0][0],
            district=self.district,
        )
        facility2 = self.create_facility(
            name="Test Facility Unique 2",
            facility_type=FACILITY_TYPES[0][0],
            district=self.district,
        )
        FacilityUser.objects.create(
            facility=facility1, user=user1, created_by=self.user
        )
        FacilityUser.objects.create(
            facility=facility2, user=user1, created_by=self.user
        )
        response = self.client.get(
            f"/api/v1/users/{self.user.username}/get_facilities/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]["name"], "Test Facility Unique 1")
        self.assertEqual(response.data[1]["name"], "Test Facility Unique 2")
