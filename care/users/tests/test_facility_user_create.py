from rest_framework import status

from care.facility.models import FacilityUser
from care.users.models import User
from care.utils.tests.test_base import TestBase


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
            "username": obj.username,
            "first_name": obj.first_name,
            "last_name": obj.last_name,
            "email": obj.email,
            "phone_number": obj.phone_number,
            "age": obj.age,
            "local_body": getattr(obj.local_body, "id", None),
            "district": getattr(obj.district, "id", None),
            "state": getattr(obj.state, "id", None),
            "skills": list(obj.skills.all()),
            "alt_phone_number": obj.alt_phone_number,
            "asset": obj.asset,
            "pf_endpoint": obj.pf_endpoint,
            "pf_p256dh": obj.pf_p256dh,
            "pf_auth": obj.pf_auth,
            "ward": getattr(obj.ward, "id", None)
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
