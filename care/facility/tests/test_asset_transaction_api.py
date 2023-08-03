from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase

from care.facility.api.viewsets.asset import AssetTransactionViewSet
from care.facility.models import Asset, AssetLocation, AssetTransaction
from care.facility.tests.mixins import TestClassMixin
from care.utils.tests.test_base import TestBase


class AssetTransactionViewSetTestCase(TestBase, TestClassMixin, APITestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        state = self.create_state()
        district = self.create_district(state=state)
        self.user = self.create_user(district=district, username="test user")
        facility = self.create_facility(district=district, user=self.user)
        self.asset_from_location = AssetLocation.objects.create(
            name="asset from location", location_type=1, facility=facility
        )
        self.asset_to_location = AssetLocation.objects.create(
            name="asset to location", location_type=1, facility=facility
        )
        self.asset = Asset.objects.create(
            name="Test Asset", current_location=self.asset_from_location, asset_type=50
        )
        self.asset_transaction = AssetTransaction.objects.create(
            asset=self.asset,
            from_location=self.asset_from_location,
            to_location=self.asset_to_location,
            performed_by=self.user,
        )

    def test_list_asset_transactions(self):
        response = self.new_request(
            ("/api/v1/asset_transaction/",),
            {"get": "list"},
            AssetTransactionViewSet,
            self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_asset_transaction(self):
        response = self.new_request(
            (f"/api/v1/asset_transaction/{self.asset_transaction.id}/",),
            {"get": "retrieve"},
            AssetTransactionViewSet,
            self.user,
            {"pk": self.asset_transaction.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
