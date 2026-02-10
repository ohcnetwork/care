from django.urls import reverse
from rest_framework import status
from care.utils.tests.base import CareAPITestBase

class TestFacilityPartialUpdate(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.super_user = self.create_super_user(username="facility_admin")
        self.client.force_authenticate(user=self.super_user)
        self.facility = self.create_facility(
            user=self.super_user,
            name="Original Facility Name",
        )

        self.detail_url = reverse(
            "facility-detail",
            kwargs={"external_id": self.facility.external_id},
        )

    def test_patch_facility_with_partial_payload_updates_only_given_fields(self):
        original_description = self.facility.description
        original_address = self.facility.address
        original_phone_number = self.facility.phone_number
        original_pincode = self.facility.pincode
        original_is_public = self.facility.is_public
        original_facility_type = self.facility.facility_type

        payload = {"name": "Patched Facility Name"}

        response = self.client.patch(self.detail_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.facility.refresh_from_db()

        self.assertEqual(self.facility.name, payload["name"])
        self.assertEqual(self.facility.description, original_description)
        self.assertEqual(self.facility.address, original_address)
        self.assertEqual(self.facility.phone_number, original_phone_number)
        self.assertEqual(self.facility.pincode, original_pincode)
        self.assertEqual(self.facility.is_public, original_is_public)
        self.assertEqual(self.facility.facility_type, original_facility_type)
