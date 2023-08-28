from enum import Enum

from django.db import transaction
from django.utils.timezone import datetime, make_aware
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework_simplejwt.tokens import RefreshToken

from care.facility.api.viewsets.asset import AssetViewSet
from care.facility.models import Asset, AssetLocation, User, UserDefaultAssetLocation
from care.facility.tests.mixins import TestClassMixin
from care.utils.assetintegration.asset_classes import AssetClasses
from care.utils.tests.test_base import TestBase


class ExpectedAssetListKeys(Enum):
    ID = "id"
    NAME = "name"
    ASSET_CLASS = "asset_class"
    IS_WORKING = "is_working"
    LOCATION_OBJECT = "location_object"


class ExpectedLocationObjectKeys(Enum):
    ID = "id"
    FACILITY = "facility"
    CREATED_DATE = "created_date"
    MODIFIED_DATE = "modified_date"
    NAME = "name"
    DESCRIPTION = "description"
    LOCATION_TYPE = "location_type"


class ExpectedFacilityKeys(Enum):
    ID = "id"
    NAME = "name"


class ExpectedAssetRetrieveKeys(Enum):
    ID = "id"
    STATUS = "status"
    ASSET_TYPE = "asset_type"
    CREATED_DATE = "created_date"
    MODIFIED_DATE = "modified_date"
    NAME = "name"
    DESCRIPTION = "description"
    ASSET_CLASS = "asset_class"
    IS_WORKING = "is_working"
    NOT_WORKING_REASON = "not_working_reason"
    SERIAL_NUMBER = "serial_number"
    WARRANTY_DETAILS = "warranty_details"
    META = "meta"
    VENDOR_NAME = "vendor_name"
    SUPPORT_NAME = "support_name"
    SUPPORT_PHONE = "support_phone"
    SUPPORT_EMAIL = "support_email"
    QR_CODE_ID = "qr_code_id"
    MANUFACTURER = "manufacturer"
    WARRANTY_AMC_END_OF_VALIDITY = "warranty_amc_end_of_validity"
    LAST_SERVICE = "last_service"
    LOCATION_OBJECT = "location_object"


class AssetViewSetTestCase(TestBase, TestClassMixin):
    endpoint = "/api/v1/asset/"
    asset_id = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.factory = APIRequestFactory()
        state = cls.create_state()
        district = cls.create_district(state=state)
        cls.user = cls.create_user(district=district, username="test user")
        cls.state_admin = cls.create_user(
            district=district,
            username="state",
            user_type=User.TYPE_VALUE_MAP["StateLabAdmin"],
        )
        cls.facility = cls.create_facility(
            district=district,
            user=cls.user,
            middleware_address="dev_middleware.coronasafe.live",
        )

        cls.asset1_location = AssetLocation.objects.create(
            name="asset1 location", location_type=1, facility=cls.facility
        )
        cls.asset = Asset.objects.create(
            name="Test Asset",
            current_location=cls.asset1_location,
            asset_type=50,
            warranty_amc_end_of_validity=make_aware(datetime(2021, 4, 1)),
            asset_class=AssetClasses.ONVIF.name,
            meta={
                "asset_type": "CAMERA",
                "local_ip_address": "192.168.0.65",
                "camera_access_key": "remoteuser:aeAE55L5Po*S*C5:3af9acd0-2d4a-49e4-bb72-45cf7be0ae65",
                "middleware_hostname": "ka-kr-mysore.10bedicu.in",
            },
        )

    def setUp(self):
        # Refresh token to header
        refresh_token = RefreshToken.for_user(self.state_admin)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh_token.access_token}"
        )

    def test_list_assets(self):
        # is user is superuser
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(self.super_user).access_token}"
        )
        response = client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.json()["results"], list)

        # is user is state lab admin
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(self.state_admin).access_token}"
        )
        response = client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.json()["results"], list)

        # Ensure only necessary data is being sent and no extra data
        expected_keys = [key.value for key in ExpectedAssetListKeys]

        data = response.json()["results"][0]

        self.assertCountEqual(data.keys(), expected_keys)
        location_object_keys = [key.value for key in ExpectedLocationObjectKeys]
        self.assertCountEqual(data["location_object"].keys(), location_object_keys)
        facility_keys = [key.value for key in ExpectedFacilityKeys]
        self.assertCountEqual(data["location_object"]["facility"].keys(), facility_keys)

    def test_create_asset(self):
        sample_data = {
            "name": "Test Asset",
            "current_location": self.asset1_location.pk,
            "asset_type": 50,
            "location": self.asset1_location.external_id,
        }
        response = self.new_request(
            (self.endpoint, sample_data, "json"),
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
        response = self.client.post("/api/v1/asset/", sample_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_asset(self):
        response = self.client.get(f"{self.endpoint}{self.asset.external_id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # Check if the expected keys are coming in the json response
        expected_keys = [key.value for key in ExpectedAssetRetrieveKeys]
        self.assertCountEqual(data.keys(), expected_keys)

    def test_update_asset(self):
        sample_data = {
            "name": "Updated Test Asset",
            "current_location": self.asset1_location.pk,
            "asset_type": 50,
            "location": self.asset1_location.external_id,
        }
        response = self.new_request(
            (f"{self.endpoint}{self.asset.external_id}", sample_data, "json"),
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

    def test_delete_asset(self):
        with transaction.atomic():
            response = self.new_request(
                (f"{self.endpoint}{self.asset.external_id}",),
                {"delete": "destroy"},
                AssetViewSet,
                self.user,
                {"external_id": self.asset.external_id},
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Asset.objects.filter(pk=self.asset.pk).exists(), True)

    def test_get_default_user_location(self):
        UserDefaultAssetLocation.objects.create(
            user=self.user, location=self.asset1_location
        )
        response = self.new_request(
            (self.endpoint,),
            {"get": "get_default_user_location"},
            AssetViewSet,
            self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

        response = self.client.get("/api/v1/asset/?in_use_by_consultation=false")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_set_default_user_location_invalid_location(self):
        sample_data = {"location": self.asset1_location.external_id}
        response = self.new_request(
            (self.endpoint, sample_data, "json"),
            {"post": "set_default_user_location"},
            AssetViewSet,
            self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        sample_data = {"location": self.asset1_location.external_id}
        UserDefaultAssetLocation.objects.create(
            user=self.user, location=self.asset1_location
        )
        response = self.new_request(
            (self.endpoint, sample_data, "json"),
            {"post": "set_default_user_location"},
            AssetViewSet,
            self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # tests invalid location
        sample_data = {"location": "invalid_location_id"}

        response = self.new_request(
            (self.endpoint, sample_data, "json"),
            {"post": "set_default_user_location"},
            AssetViewSet,
            self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # tests invalid location
        sample_data = {"location": "invalid_location_id"}

        response = self.new_request(
            (self.endpoint, sample_data, "json"),
            {"post": "set_default_user_location"},
            AssetViewSet,
            self.user,
        )

        # tests providing no location
        sample_data = {}
        response = self.new_request(
            (self.endpoint, sample_data, "json"),
            {"post": "set_default_user_location"},
            AssetViewSet,
            self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"location": "is required"})
