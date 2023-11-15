from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase

from care.facility.api.viewsets.asset import AssetViewSet
from care.facility.models import Asset, AssetBed, AssetLocation, Bed
from care.utils.tests.test_utils import TestUtils


class AssetViewSetTestCase(TestUtils, APITestCase):
    asset_id = None

    def setUpTestData(self):
        self.factory = APIRequestFactory()
        state = self.create_state()
        district = self.create_district(state=state)
        self.user = self.create_user(district=district, username="test user")
        facility = self.create_facility(district=district, user=self.user)
        self.asset1_location = AssetLocation.objects.create(
            name="asset1 location", location_type=1, facility=facility
        )

        # depends upon the operational dev camera config
        self.onvif_meta = {
            "asset_type": "CAMERA",
            "local_ip_address": "192.168.1.64",
            "camera_access_key": "remote_user:2jCkrCRSeahzKEU:d5694af2-21e2-4a39-9bad-2fb98d9818bd",
            "middleware_hostname": "dev_middleware.coronasafe.live",
        }
        self.hl7monitor_meta = {}
        self.ventilator_meta = {}
        self.bed = Bed.objects.create(
            name="Test Bed",
            facility=facility,
            location=self.asset1_location,
            meta={},
            bed_type=1,
        )
        self.asset: Asset = Asset.objects.create(
            name="Test Asset",
            current_location=self.asset1_location,
            asset_type=50,
        )

    def test_onvif_relative_move(self):
        self.asset.asset_class = "ONVIF"
        self.asset.meta = self.onvif_meta
        self.asset.save()
        boundary_asset_bed = AssetBed.objects.create(
            asset=self.asset,
            bed=self.bed,
            meta={
                "range": {
                    "max_x": 2,
                    "min_x": -2,
                    "max_y": 2,
                    "min_y": -2,
                }
            },
        )
        sample_data = {
            "action": {
                "type": "relative_move",
                "data": {
                    "x": 0.1,
                    "y": 0.1,
                    "zoom": 0.1,
                    "camera_state": {"x": 1.5, "y": 1.5, "zoom": 0},
                    "id": boundary_asset_bed.external_id,
                },
            }
        }
        response = self.new_request(
            (
                f"/api/v1/asset/{self.asset.external_id}/operate_assets/",
                sample_data,
                "json",
            ),
            {"post": "operate_assets"},
            AssetViewSet,
            self.user,
            {"external_id": self.asset.external_id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        sample_data_invald = {
            "action": {
                "type": "relative_move",
                "data": {
                    "x": 0.6,
                    "y": 0.1,
                    "zoom": 0.1,
                    "camera_state": {"x": 1.5, "y": 1.5, "zoom": 0},
                    "id": boundary_asset_bed.external_id,
                },
            }
        }
        response_invalid = self.new_request(
            (
                f"/api/v1/asset/{self.asset.external_id}/operate_assets/",
                sample_data_invald,
                "json",
            ),
            {"post": "operate_assets"},
            AssetViewSet,
            self.user,
            {"external_id": self.asset.external_id},
        )

        self.assertEqual(response_invalid.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response_invalid.data.get("message", {}).get("action", {}).code, "invalid"
        )

    def test_hl7monitor(self):
        self.asset.asset_class = "HL7MONITOR"
        self.asset.meta = self.hl7monitor_meta
        self.asset.save()
        pass

    def test_ventilator(self):
        self.asset.asset_class = "VENTILATOR"
        self.asset.meta = self.ventilator_meta
        self.asset.save()
        pass
