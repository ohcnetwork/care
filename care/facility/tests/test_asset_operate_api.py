from rest_framework import status
from rest_framework.test import APITestCase

from care.facility.models import AssetBed
from care.utils.tests.test_utils import TestUtils


class AssetViewSetTestCase(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.state = cls.create_state()
        cls.district = cls.create_district(state=cls.state)
        cls.user = cls.create_user(district=cls.district, username="test user")
        cls.facility = cls.create_facility(district=cls.district, user=cls.user)
        cls.asset1_location = cls.create_asset_location(facility=cls.facility)

        # depends upon the operational dev camera config
        cls.onvif_meta = {
            "asset_type": "CAMERA",
            "local_ip_address": "192.168.1.64",
            "camera_access_key": "remote_user:2jCkrCRSeahzKEU:d5694af2-21e2-4a39-9bad-2fb98d9818bd",
            "middleware_hostname": "dev_middleware.coronasafe.live",
        }
        cls.hl7monitor_meta = {}
        cls.ventilator_meta = {}
        cls.bed = cls.create_bed(
            facility=cls.facility, location=cls.asset1_location, meta={}
        )
        cls.asset = cls.create_asset(location=cls.asset1_location)

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
        response = self.client.post(
            f"/api/v1/asset/{self.asset.external_id}/operate_assets/",
            sample_data,
            format="json",
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
        response_invalid = self.client.post(
            f"/api/v1/asset/{self.asset.external_id}/operate_assets/",
            sample_data_invald,
            "json",
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
