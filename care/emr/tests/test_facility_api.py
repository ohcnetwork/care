from django.urls import reverse
from rest_framework import status

from care.facility.models.facility import REVERSE_FACILITY_TYPES
from care.utils.tests.base import CareAPITestBase


class TestFacilityViewSet(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.superuser = self.create_super_user()
        self.user = self.create_user()
        self.geo_organization = self.create_organization(org_type="govt")
        self.facility = self.create_facility(
            user=self.superuser,
            name="Test Facility",
            facility_type=2,
            pincode=123456,
        )
        self.client.force_authenticate(user=self.superuser)
        self.base_url = reverse("facility-list")

    def _get_detail_url(self, facility_id):
        return reverse(
            "facility-detail",
            kwargs={"external_id": facility_id},
        )

    def _get_facility_data(self, **overrides):
        data = {
            "name": "New Facility",
            "description": "Test desc",
            "facility_type": REVERSE_FACILITY_TYPES[2],
            "address": "Test Address",
            "pincode": 123456,
            "phone_number": "+911234567890",
            "is_public": True,
            "geo_organization": str(self.geo_organization.external_id),
            "features": [],
        }
        data.update(overrides)
        return data

    def test_create_facility(self):
        data = self._get_facility_data()
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "New Facility")

    def test_create_facility_duplicate_name(self):
        data = self._get_facility_data(name="Test Facility")
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_facilities(self):
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data["results"]), 1)

    def test_retrieve_facility(self):
        url = self._get_detail_url(self.facility.external_id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], str(self.facility.external_id))

    def test_update_facility(self):
        url = self._get_detail_url(self.facility.external_id)
        data = self._get_facility_data(name="Updated Facility")
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Updated Facility")

    def test_delete_facility_as_superuser(self):
        facility = self.create_facility(
            user=self.superuser, name="To Delete", facility_type=2
        )
        url = self._get_detail_url(facility.external_id)
        response = self.client.delete(url)
        self.assertIn(response.status_code, [204, 200])

    def test_delete_facility_as_non_superuser(self):
        self.client.force_authenticate(user=self.user)
        url = self._get_detail_url(self.facility.external_id)
        response = self.client.delete(url)
        self.assertIn(response.status_code, [403, 404])

    def test_create_facility_without_permission(self):
        self.client.force_authenticate(user=self.user)
        data = self._get_facility_data(name="Unauth Facility")
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_by_name(self):
        response = self.client.get(self.base_url, {"name": "Test"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for r in response.data["results"]:
            self.assertIn("Test", r["name"])

    def test_filter_by_phone_number(self):
        facility = self.create_facility(
            user=self.superuser, phone_number="+919876543210"
        )
        response = self.client.get(self.base_url, {"phone_number": "+919876543210"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            any(r["id"] == str(facility.external_id) for r in response.data["results"])
        )

    def test_delete_cover_image_when_none(self):
        url = reverse("facility-cover-image", args=[self.facility.external_id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 404)
        self.assertIn("No cover image to delete", str(response.data))


class TestAllFacilityViewSet(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.superuser = self.create_super_user()
        self.facility = self.create_facility(
            user=self.superuser, name="Public Facility", is_public=True
        )
        self.private_facility = self.create_facility(
            user=self.superuser, name="Private Facility", is_public=False
        )
        self.base_url = reverse("getallfacilities-list")

    def test_list_public_facilities_unauthenticated(self):
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [r["id"] for r in response.data["results"]]
        self.assertIn(str(self.facility.external_id), ids)
        self.assertNotIn(str(self.private_facility.external_id), ids)

    def test_search_public_facilities(self):
        response = self.client.get(self.base_url, {"search": "Public"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for r in response.data["results"]:
            self.assertIn("Public", r["name"])
