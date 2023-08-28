from enum import Enum

from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from care.facility.api.viewsets.asset import AssetPublicViewSet
from care.facility.models import Asset, AssetLocation
from care.facility.tests.mixins import TestClassMixin
from care.utils.tests.test_base import TestBase


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


class ExpectedPublicAssetRetrieveKeys(Enum):
    ID = "id"
    LOCATION_OBJECT = "location_object"
    EXTERNAL_ID = "external_id"
    CREATED_DATE = "created_date"
    MODIFIED_DATE = "modified_date"
    DELETED = "deleted"
    NAME = "name"
    ASSET_TYPE = "asset_type"
    STATUS = "status"
    IS_WORKING = "is_working"
    SERIAL_NUMBER = "serial_number"
    WARRANTY_DETAILS = "warranty_details"
    META = "meta"
    VENDOR_NAME = "vendor_name"
    SUPPORT_NAME = "support_name"
    SUPPORT_PHONE = "support_phone"
    SUPPORT_EMAIL = "support_email"
    CURRENT_LOCATION = "current_location"
    LAST_SERVICE = "last_service"


class AssetPublicViewSetTestCase(TestBase, TestClassMixin, APITestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        state = self.create_state()
        district = self.create_district(state=state)
        self.user = self.create_user(district=district, username="test user")
        facility = self.create_facility(district=district, user=self.user)
        # Add access token to the authorization header of test request
        refresh_token = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh_token.access_token}"
        )
        self.asset_location = AssetLocation.objects.create(
            name="asset1 location", location_type=1, facility=facility
        )
        self.asset = Asset.objects.create(
            name="Test Asset", current_location=self.asset_location, asset_type=50
        )

    def test_retrieve_asset(self):
        response = self.client.get(f"/api/v1/public/asset/{self.asset.external_id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        expected_keys = [key.value for key in ExpectedPublicAssetRetrieveKeys]
        self.assertCountEqual(data.keys(), expected_keys)
        location_object_keys = [key.value for key in ExpectedLocationObjectKeys]
        self.assertCountEqual(data["location_object"].keys(), location_object_keys)
        facility_keys = [key.value for key in ExpectedFacilityKeys]
        self.assertCountEqual(data["location_object"]["facility"].keys(), facility_keys)

    def test_retrieve_cached_asset(self):
        key = "asset:" + str(self.asset.external_id)
        cache.set(key, {"name": "Cached Asset"}, 60 * 60 * 24)

        response = self.new_request(
            (f"/api/v1/public/asset/{self.asset.external_id}/",),
            {"get": "retrieve"},
            AssetPublicViewSet,
            self.user,
            {"external_id": str(self.asset.external_id)},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Cached Asset")

    def test_retrieve_nonexistent_asset(self):
        response = self.new_request(
            ("/api/v1/public/asset/nonexistent/",),
            {"get": "retrieve"},
            AssetPublicViewSet,
            self.user,
            {"external_id": "nonexistent"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
