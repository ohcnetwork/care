from django.db import transaction
from django.utils.timezone import datetime, make_aware
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase

from care.facility.api.viewsets.asset import AssetViewSet
from care.facility.models import Asset, AssetLocation, User, UserDefaultAssetLocation
from care.facility.tests.mixins import TestClassMixin
from care.utils.tests.test_base import TestBase


class AssetViewSetTestCase(TestBase, TestClassMixin, APITestCase):
    asset_id = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.factory = APIRequestFactory()
        state = cls.create_state()
        district = cls.create_district(state=state)
        cls.user = cls.create_user(district=district, username="test user")
        facility = cls.create_facility(district=district, user=cls.user)
        cls.asset1_location = AssetLocation.objects.create(
            name="asset1 location", location_type=1, facility=facility
        )
        cls.asset = Asset.objects.create(
            name="Test Asset",
            current_location=cls.asset1_location,
            asset_type=50,
            warranty_amc_end_of_validity=make_aware(datetime(2021, 4, 1)),
        )

    def test_list_assets(self):
        response = self.new_request(
            ("/api/v1/asset/",), {"get": "list"}, AssetViewSet, self.user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_asset(self):
        sample_data = {
            "name": "Test Asset",
            "current_location": self.asset1_location.pk,
            "asset_type": 50,
            "location": self.asset1_location.external_id,
        }
        response = self.new_request(
            ("/api/v1/asset/", sample_data, "json"),
            {"post": "create"},
            AssetViewSet,
            self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_asset_with_warranty_past(self):
        sample_data = {
            "name": "Test Asset",
            "current_location": self.asset1_location.pk,
            "asset_type": 50,
            "location": self.asset1_location.external_id,
            "warranty_amc_end_of_validity": "2000-04-01",
        }
        response = self.new_request(
            ("/api/v1/asset/", sample_data, "json"),
            {"post": "create"},
            AssetViewSet,
            self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_asset(self):
        response = self.new_request(
            (f"/api/v1/asset/{self.asset.external_id}",),
            {"get": "retrieve"},
            AssetViewSet,
            self.user,
            {"external_id": self.asset.external_id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_asset(self):
        sample_data = {
            "name": "Updated Test Asset",
            "current_location": self.asset1_location.pk,
            "asset_type": 50,
            "location": self.asset1_location.external_id,
        }
        response = self.new_request(
            (f"/api/v1/asset/{self.asset.external_id}", sample_data, "json"),
            {"patch": "partial_update"},
            AssetViewSet,
            self.user,
            {"external_id": self.asset.external_id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], sample_data["name"])
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.name, sample_data["name"])

    def test_update_asset_change_warranty_improperly(self):
        sample_data = {
            "warranty_amc_end_of_validity": "2002-04-01",
        }
        response = self.new_request(
            (f"/api/v1/asset/{self.asset.external_id}", sample_data, "json"),
            {"patch": "partial_update"},
            AssetViewSet,
            self.user,
            {"external_id": self.asset.external_id},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_asset_change_warranty_properly(self):
        sample_data = {
            "warranty_amc_end_of_validity": "2222-04-01",
        }
        response = self.new_request(
            (f"/api/v1/asset/{self.asset.external_id}", sample_data, "json"),
            {"patch": "partial_update"},
            AssetViewSet,
            self.user,
            {"external_id": self.asset.external_id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_asset(self):
        with transaction.atomic():
            response = self.new_request(
                (f"/api/v1/asset/{self.asset.external_id}",),
                {"delete": "destroy"},
                AssetViewSet,
                self.user,
                {"external_id": self.asset.external_id},
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Asset.objects.filter(pk=self.asset.pk).exists(), True)
        self.user.user_type = User.TYPE_VALUE_MAP["DistrictAdmin"]
        self.user.save()
        response = self.new_request(
            (f"/api/v1/asset/{self.asset.external_id}",),
            {"delete": "destroy"},
            AssetViewSet,
            self.user,
            {"external_id": self.asset.external_id},
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Asset.objects.filter(pk=self.asset.pk).exists(), False)

    def test_set_default_user_location_invalid_location(self):
        # tests invalid location
        sample_data = {"location": "invalid_location_id"}

        response = self.new_request(
            ("/api/v1/asset/", sample_data, "json"),
            {"post": "set_default_user_location"},
            AssetViewSet,
            self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # tests providing no location
        sample_data = {}
        response = self.new_request(
            ("/api/v1/asset/", sample_data, "json"),
            {"post": "set_default_user_location"},
            AssetViewSet,
            self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"location": "is required"})

    def test_get_default_user_location(self):
        UserDefaultAssetLocation.objects.create(
            user=self.user, location=self.asset1_location
        )
        response = self.new_request(
            ("/api/v1/asset/",),
            {"get": "get_default_user_location"},
            AssetViewSet,
            self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, self.asset1_location.external_id)
