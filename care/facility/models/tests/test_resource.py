from rest_framework import status
from rest_framework.test import APITestCase

from care.utils.tests.test_utils import TestUtils


class ResourceTransferTest(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.user = cls.create_user("staff1", cls.district, home_facility=cls.facility)
        cls.patient = cls.create_patient(cls.district, cls.facility)

    def test_with_invalid_facilityid_input(self):
        dist_admin = self.create_user("dist_admin", self.district, user_type=30)
        sample_data = {
            "approving_facility": self.facility.external_id,
            "category": "OXYGEN",
            "emergency": "false",
            "origin_facility": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",  # invalid facility id
            "reason": "adadasa",
            "refering_facility_contact_name": "rash",
            "refering_facility_contact_number": "+918888888889",
            "requested_quantity": "10",
            "status": "PENDING",
            "sub_category": 110,
            "title": "a",
        }
        self.client.force_authenticate(user=dist_admin)
        response = self.client.post("/api/v1/resource/", sample_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("origin_facility", response.data)
