from rest_framework import status
from rest_framework.test import APITestCase

from care.utils.assetintegration.asset_classes import AssetClasses
from care.utils.tests.test_utils import TestUtils
from config.authentication import MiddlewareUser


class MiddlewareConfigTestCase(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.hostname = "test-middleware.com"
        cls.facility = cls.create_facility(
            cls.super_user,
            cls.district,
            cls.local_body,
            middleware_address=cls.hostname,
        )
        cls.middleware_user = MiddlewareUser(facility=cls.facility)

    def setUp(self) -> None:
        self.client.force_authenticate(user=self.middleware_user)

    def test_fetch_middleware_config_hostname_on_facility(self):
        test_location = self.create_asset_location(self.facility)
        test_asset = self.create_asset(
            test_location,
            asset_class=AssetClasses.HL7MONITOR.name,
            meta={"local_ip_address": "192.168.1.14"},
        )
        response = self.client.get(
            f"/api/v1/asset_config/?middleware_hostname={self.hostname}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["id"], str(test_asset.external_id))

    def test_fetch_middleware_config_hostname_on_facility_location(self):
        test_location = self.create_asset_location(
            self.facility, middleware_address=self.hostname
        )
        test_asset = self.create_asset(
            test_location,
            asset_class=AssetClasses.HL7MONITOR.name,
            meta={"local_ip_address": "192.168.1.14"},
        )
        response = self.client.get(
            f"/api/v1/asset_config/?middleware_hostname={self.facility.middleware_address}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["id"], str(test_asset.external_id))

    def test_fetch_middleware_config_hostname_on_facility_asset(self):
        test_location = self.create_asset_location(self.facility)
        test_asset = self.create_asset(
            test_location,
            asset_class=AssetClasses.HL7MONITOR.name,
            meta={
                "local_ip_address": "192.168.1.14",
                "middleware_hostname": self.hostname,
            },
        )
        response = self.client.get(
            f"/api/v1/asset_config/?middleware_hostname={self.facility.middleware_address}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["id"], str(test_asset.external_id))

    def test_fetch_middleware_config_hostname_on_facility_location_asset(self):
        test_location = self.create_asset_location(
            self.facility, middleware_address=self.hostname
        )
        test_asset = self.create_asset(
            test_location,
            asset_class=AssetClasses.HL7MONITOR.name,
            meta={
                "local_ip_address": "192.168.1.14",
                "middleware_hostname": self.hostname,
            },
        )
        response = self.client.get(
            f"/api/v1/asset_config/?middleware_hostname={self.facility.middleware_address}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["id"], str(test_asset.external_id))

    def test_fetch_middleware_config_different_hostname_on_location_same_on_asset(self):
        test_location = self.create_asset_location(
            self.facility, middleware_address="not-test-middleware.com"
        )
        test_asset = self.create_asset(
            test_location,
            asset_class=AssetClasses.HL7MONITOR.name,
            meta={
                "local_ip_address": "192.168.1.14",
                "middleware_hostname": self.hostname,
            },
        )
        response = self.client.get(
            f"/api/v1/asset_config/?middleware_hostname={self.facility.middleware_address}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["id"], str(test_asset.external_id))

    def test_fetch_middleware_config_different_hostname_on_location(self):
        test_location = self.create_asset_location(
            self.facility, middleware_address="not-test-middleware.com"
        )
        self.create_asset(
            test_location,
            asset_class=AssetClasses.HL7MONITOR.name,
            meta={"local_ip_address": "192.168.1.14"},
        )
        response = self.client.get(
            f"/api/v1/asset_config/?middleware_hostname={self.facility.middleware_address}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_fetch_middleware_config_different_hostname_on_asset_same_on_location(self):
        test_location = self.create_asset_location(
            self.facility, middleware_address=self.hostname
        )
        test_asset = self.create_asset(
            test_location,
            asset_class=AssetClasses.HL7MONITOR.name,
            meta={
                "local_ip_address": "192.168.1.14",
                "middleware_hostname": "not-test-middleware.com",
            },
        )
        response = self.client.get(
            "/api/v1/asset_config/?middleware_hostname=not-test-middleware.com"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["id"], str(test_asset.external_id))
