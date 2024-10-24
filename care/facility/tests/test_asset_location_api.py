from rest_framework import status
from rest_framework.test import APITestCase

from care.utils.assetintegration.asset_classes import AssetClasses
from care.utils.tests.test_utils import TestUtils


class AssetLocationViewSetTestCase(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.asset_location = cls.create_asset_location(cls.facility)
        cls.asset_location_with_linked_bed = cls.create_asset_location(cls.facility)
        cls.asset_location_with_linked_asset = cls.create_asset_location(cls.facility)
        cls.asset = cls.create_asset(
            cls.asset_location_with_linked_asset,
            asset_class=AssetClasses.HL7MONITOR.name,
        )
        cls.bed = cls.create_bed(cls.facility, cls.asset_location_with_linked_bed)
        cls.asset_bed = cls.create_asset_bed(cls.asset, cls.bed)
        cls.patient = cls.create_patient(cls.district, cls.facility)
        cls.consultation = cls.create_consultation(cls.patient, cls.facility)
        cls.consultation_bed = cls.create_consultation_bed(cls.consultation, cls.bed)
        cls.user = cls.create_user("staff", cls.district, home_facility=cls.facility)
        cls.deleted_asset = cls.create_asset(cls.asset_location)
        cls.deleted_asset.deleted = True
        cls.deleted_asset.save()
        cls.asset_second_location = cls.create_asset_location(
            cls.facility, name="asset2 location"
        )
        cls.asset_second = cls.create_asset(
            cls.asset_second_location, asset_class=AssetClasses.HL7MONITOR.name
        )
        cls.asset_bed_second = cls.create_bed(cls.facility, cls.asset_second_location)
        cls.assetbed_second = cls.create_asset_bed(
            cls.asset_second, cls.asset_bed_second
        )

    def test_list_asset_locations(self):
        response = self.client.get(
            f"/api/v1/facility/{self.facility.external_id}/asset_location/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, self.asset_location.external_id)
        self.assertContains(response, self.asset_second_location.external_id)

    def test_asset_locations_get_monitors_all(self):
        response = self.client.get(
            f"/api/v1/facility/{self.facility.external_id}/asset_location/?bed_is_occupied=false"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, self.asset_location_with_linked_bed.external_id)
        self.assertContains(response, self.asset_second_location.external_id)

    def test_asset_locations_get_monitors_only_consultation_bed(self):
        response = self.client.get(
            f"/api/v1/facility/{self.facility.external_id}/asset_location/?bed_is_occupied=true"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, self.asset_location_with_linked_bed.external_id)

    def test_asset_locations_get_only_monitors(self):
        self.asset.asset_class = AssetClasses.VENTILATOR.name
        self.asset.save()
        response = self.client.get(
            f"/api/v1/facility/{self.facility.external_id}/asset_location/?bed_is_occupied=false"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, self.asset_second_location.external_id)
        self.assertEqual(len(response.data["results"]), 1)

    def test_retrieve_asset_location(self):
        response = self.client.get(
            f"/api/v1/facility/{self.facility.external_id}/asset_location/{self.asset_location.external_id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], str(self.asset_location.external_id))
        self.assertEqual(
            response.data["middleware_address"], self.asset_location.middleware_address
        )

    def test_create_asset_location(self):
        sample_data = {
            "name": "Test Asset Location",
            "middleware_address": "example.com",
            "location_type": "ICU",
        }
        response = self.client.post(
            f"/api/v1/facility/{self.facility.external_id}/asset_location/",
            sample_data,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], sample_data["name"])
        self.assertEqual(
            response.data["middleware_address"], sample_data["middleware_address"]
        )

    def test_update_asset_location(self):
        sample_data = {
            "name": "Updated Test Asset Location",
            "middleware_address": "updated.example.com",
            "location_type": "WARD",
        }
        response = self.client.patch(
            f"/api/v1/facility/{self.facility.external_id}/asset_location/{self.asset_location.external_id}/",
            sample_data,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], sample_data["name"])
        self.assertEqual(
            response.data["middleware_address"], sample_data["middleware_address"]
        )

    def test_create_asset_location_invalid_middleware(self):
        sample_data = {
            "name": "Test Asset Location",
            "middleware_address": "https://invalid.middleware.///",
            "location_type": "OTHER",
        }
        response = self.client.post(
            f"/api/v1/facility/{self.facility.external_id}/asset_location/",
            sample_data,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["middleware_address"][0].code, "invalid_domain_name"
        )

    def test_delete_asset_location_with_beds(self):
        response = self.client.delete(
            f"/api/v1/facility/{self.facility.external_id}/asset_location/{self.asset_location_with_linked_bed.external_id}/",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data[0], "Cannot delete a Location with associated Beds"
        )

    def test_delete_asset_location_with_linked_assets(self):
        response = self.client.delete(
            f"/api/v1/facility/{self.facility.external_id}/asset_location/{self.asset_location_with_linked_asset.external_id}/",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data[0], "Cannot delete a Location with associated Assets"
        )

    def test_delete_asset_location_with_no_assets_and_beds(self):
        response = self.client.delete(
            f"/api/v1/facility/{self.facility.external_id}/asset_location/{self.asset_location.external_id}/",
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_user_access_to_asset_location_on_user_type(self):
        # when a user is a state_lab_admin or a district_lab_admin
        state_lab_admin = self.create_user(
            "state_lab_admin", self.district, user_type=35
        )
        district_lab_admin = self.create_user(
            "district_lab_admin", self.district, user_type=25
        )

        self.client.force_authenticate(user=state_lab_admin)

        # when they try to access a asset_location in their state or district then they
        # should be able to do so without permission issue
        response = self.client.get(
            f"/api/v1/facility/{self.facility.external_id}/asset_location/{self.asset_location_with_linked_bed.external_id}/"
        )

        self.assertIs(response.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=district_lab_admin)
        response = self.client.get(
            f"/api/v1/facility/{self.facility.external_id}/asset_location/{self.asset_location_with_linked_bed.external_id}/"
        )
        self.assertIs(response.status_code, status.HTTP_200_OK)
