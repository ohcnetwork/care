from rest_framework import status
from rest_framework.test import APITestCase

from care.facility.models import AssetTransaction
from care.utils.tests.test_utils import TestUtils


class AssetTransactionViewSetTestCase(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.user = cls.create_user("staff", cls.district, home_facility=cls.facility)

        cls.asset_from_location = cls.create_asset_location(
            cls.facility, name="asset from location"
        )
        cls.asset_to_location = cls.create_asset_location(
            cls.facility, name="asset to location"
        )
        cls.asset = cls.create_asset(
            cls.asset_from_location, name="Test Asset", asset_type=50
        )
        cls.asset_transaction = AssetTransaction.objects.create(
            asset=cls.asset,
            from_location=cls.asset_from_location,
            to_location=cls.asset_to_location,
            performed_by=cls.user,
        )

    def test_list_asset_transactions(self):
        response = self.client.get("/api/v1/asset_transaction/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_asset_transaction(self):
        response = self.client.get(
            f"/api/v1/asset_transaction/{self.asset_transaction.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
