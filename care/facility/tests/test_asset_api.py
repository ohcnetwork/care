from django.utils.timezone import datetime, make_aware
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase

from care.facility.models import Asset, AssetLocation, Bed, User
from care.utils.tests.test_base import TestBase


class AssetViewSetTestCase(TestBase, APITestCase):
    asset_id = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.factory = APIRequestFactory()
        state = cls.create_state()
        district = cls.create_district(state=state)
        cls.user = cls.create_user(district=district, username="test user")
        cls.facility = cls.create_facility(district=district, user=cls.user)
        cls.asset1_location = AssetLocation.objects.create(
            name="asset1 location", location_type=1, facility=cls.facility
        )
        cls.asset = Asset.objects.create(
            name="Test Asset",
            current_location=cls.asset1_location,
            asset_type=50,
            warranty_amc_end_of_validity=make_aware(datetime(2021, 4, 1)),
        )

    def test_list_assets(self):
        response = self.client.get("/api/v1/asset/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_asset(self):
        sample_data = {
            "name": "Test Asset",
            "current_location": self.asset1_location.pk,
            "asset_type": 50,
            "location": self.asset1_location.external_id,
        }
        response = self.client.post("/api/v1/asset/", sample_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_asset_with_warranty_past(self):
        sample_data = {
            "name": "Test Asset",
            "current_location": self.asset1_location.pk,
            "asset_type": 50,
            "location": self.asset1_location.external_id,
            "warranty_amc_end_of_validity": "2000-04-01",
        }
        response = self.client.post("/api/v1/asset/", sample_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_asset(self):
        response = self.client.get(f"/api/v1/asset/{self.asset.external_id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_asset(self):
        sample_data = {
            "name": "Updated Test Asset",
            "current_location": self.asset1_location.pk,
            "asset_type": 50,
            "location": self.asset1_location.external_id,
        }
        response = self.client.patch(
            f"/api/v1/asset/{self.asset.external_id}/", sample_data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], sample_data["name"])
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.name, sample_data["name"])

    def test_update_asset_change_warranty_improperly(self):
        sample_data = {
            "warranty_amc_end_of_validity": "2002-04-01",
        }
        response = self.client.patch(
            f"/api/v1/asset/{self.asset.external_id}/", sample_data
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_asset_change_warranty_properly(self):
        sample_data = {
            "warranty_amc_end_of_validity": "2222-04-01",
        }
        response = self.client.patch(
            f"/api/v1/asset/{self.asset.external_id}/", sample_data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_asset_failure(self):
        response = self.client.delete(f"/api/v1/asset/{self.asset.external_id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Asset.objects.filter(pk=self.asset.pk).exists(), True)

    def test_delete_asset(self):
        self.user.user_type = User.TYPE_VALUE_MAP["DistrictAdmin"]
        self.user.save()
        response = self.client.delete(
            f"/api/v1/asset/{self.asset.external_id}/",
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Asset.objects.filter(pk=self.asset.pk).exists(), False)

    def test_asset_filter_in_use_by_consultation(self):
        asset1 = Asset.objects.create(
            name="asset1", current_location=self.asset1_location
        )
        asset2 = Asset.objects.create(
            name="asset2", current_location=self.asset1_location
        )

        consultation = self.create_consultation()
        bed = Bed.objects.create(
            name="bed1", location=self.asset1_location, facility=self.facility
        )
        self.client.post(
            "/api/v1/consultationbed/",
            {
                "consultation": consultation.external_id,
                "bed": bed.external_id,
                "start_date": datetime.now().isoformat(),
                "assets": [asset1.external_id, asset2.external_id],
            },
        )

        response = self.client.get("/api/v1/asset/?in_use_by_consultation=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

        response = self.client.get("/api/v1/asset/?in_use_by_consultation=false")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
