from datetime import date

from rest_framework import status
from rest_framework.test import APITestCase

from care.users.models import User
from care.utils.tests.test_utils import TestUtils


class TestFacilityUserApi(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.user = cls.create_user("staff1", cls.district, home_facility=cls.facility)
        cls.state_admin = cls.create_user(
            "stateadmin1",
            cls.district,
            home_facility=cls.facility,
            user_type=User.TYPE_VALUE_MAP["StateAdmin"],
        )

    def get_base_url(self):
        return "/api/v1/users/add_user/"

    def get_list_representation(self, obj) -> dict:
        raise NotImplementedError

    def get_detail_representation(self, obj: User = None) -> dict:
        return {
            "id": obj.id,
            "user_type": obj.get_user_type_display(),
            "gender": obj.get_gender_display(),
            "username": obj.username,
            "first_name": obj.first_name,
            "last_name": obj.last_name,
            "email": obj.email,
            "phone_number": obj.phone_number,
            "date_of_birth": str(obj.date_of_birth),
            "local_body": getattr(obj.local_body, "id", None),
            "district": getattr(obj.district, "id", None),
            "state": getattr(obj.state, "id", None),
            "skills": list(obj.skills.all()),
            "alt_phone_number": obj.alt_phone_number,
            "asset": obj.asset,
            "pf_endpoint": obj.pf_endpoint,
            "pf_p256dh": obj.pf_p256dh,
            "pf_auth": obj.pf_auth,
            "ward": getattr(obj.ward, "id", None),
        }

    def get_user_data(self, **kwargs):
        data = {
            "username": "roopak",
            "user_type": "Staff",
            "phone_number": "+917795937091",
            "gender": "Male",
            "date_of_birth": date(2005, 1, 1),
            "first_name": "Roopak",
            "last_name": "A N",
            "email": "anroopak@gmail.com",
            "district": self.district.id,
            "verified": True,
            "facilities": [self.facility.external_id],
        }
        data.update(kwargs)
        return data.copy()

    def test_create_facility_user__should_fail__when_higher_level(self):
        data = self.get_user_data(user_type="DistrictAdmin")
        response = self.client.post(self.get_base_url(), data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_facility_user__should_fail__when_different_location(self):
        new_district = self.clone_object(self.district)
        data = self.get_user_data(district=new_district.id)
        response = self.client.post(self.get_base_url(), data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_user_of_same_type(self):
        self.client.force_authenticate(self.state_admin)

        data = self.get_user_data(
            username="stateadmin2", user_type=User.TYPE_VALUE_MAP["StateAdmin"]
        )
        res = self.client.post(self.get_base_url(), data=data, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        res = self.client.get("/api/v1/users/", {"username": "stateadmin2"})
        self.assertContains(res, "stateadmin2")
