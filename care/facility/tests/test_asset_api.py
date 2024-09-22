from django.utils.timezone import now, timedelta
from rest_framework import status
from rest_framework.test import APITestCase

from care.facility.models import Asset, Bed
from care.users.models import User
from care.utils.assetintegration.asset_classes import AssetClasses
from care.utils.tests.test_utils import TestUtils


class AssetViewSetTestCase(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.asset_location = cls.create_asset_location(cls.facility)
        cls.user = cls.create_user("staff", cls.district, home_facility=cls.facility)
        cls.state_admin_ro = cls.create_user(
            "stateadmin-ro",
            cls.district,
            user_type=User.TYPE_VALUE_MAP["StateReadOnlyAdmin"],
        )
        cls.patient = cls.create_patient(
            cls.district, cls.facility, local_body=cls.local_body
        )

    def setUp(self) -> None:
        super().setUp()
        self.asset = self.create_asset(self.asset_location)

    def test_list_assets(self):
        response = self.client.get("/api/v1/asset/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_asset(self):
        sample_data = {
            "name": "Test Asset",
            "asset_type": 50,
            "location": self.asset_location.external_id,
        }
        response = self.client.post("/api/v1/asset/", sample_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_asset_read_only(self):
        sample_data = {
            "name": "Test Asset",
            "asset_type": 50,
            "location": self.asset_location.external_id,
        }
        self.client.force_authenticate(self.state_admin_ro)
        response = self.client.post("/api/v1/asset/", sample_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_asset_with_warranty_past(self):
        sample_data = {
            "name": "Test Asset",
            "asset_type": 50,
            "location": self.asset_location.external_id,
            "warranty_amc_end_of_validity": "2000-04-01",
        }
        response = self.client.post("/api/v1/asset/", sample_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_asset(self):
        response = self.client.get(f"/api/v1/asset/{self.asset.external_id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("latest_status", response.data)

    def test_update_asset(self):
        sample_data = {
            "name": "Updated Test Asset",
            "asset_type": 50,
            "location": self.asset_location.external_id,
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
        user = self.create_user(
            "distadmin", self.district, home_facility=self.facility, user_type=30
        )
        self.client.force_authenticate(user=user)
        response = self.client.delete(
            f"/api/v1/asset/{self.asset.external_id}/",
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Asset.objects.filter(pk=self.asset.pk).exists(), False)

    def test_asset_filter_in_use_by_consultation(self):
        asset1 = Asset.objects.create(
            name="asset1", current_location=self.asset_location
        )
        asset2 = Asset.objects.create(
            name="asset2", current_location=self.asset_location
        )

        consultation = self.create_consultation(self.patient, self.facility)
        bed = Bed.objects.create(
            name="bed1", location=self.asset_location, facility=self.facility
        )
        self.client.post(
            "/api/v1/consultationbed/",
            {
                "consultation": consultation.external_id,
                "bed": bed.external_id,
                "start_date": now().isoformat(),
                "assets": [asset1.external_id, asset2.external_id],
            },
        )

        response = self.client.get("/api/v1/asset/?in_use_by_consultation=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

        response = self.client.get("/api/v1/asset/?in_use_by_consultation=false")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_asset_filter_warranty_amc_end_of_validity(self):
        asset1 = Asset.objects.create(
            name="asset1",
            current_location=self.asset_location,
            warranty_amc_end_of_validity=now().date(),
        )
        asset2 = Asset.objects.create(
            name="asset2",
            current_location=self.asset_location,
            warranty_amc_end_of_validity=now().date() + timedelta(days=1),
        )

        response = self.client.get(
            f"/api/v1/asset/?warranty_amc_end_of_validity_before={now().date() + timedelta(days=2)}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(
            str(asset1.external_id), [asset["id"] for asset in response.data["results"]]
        )
        self.assertIn(
            str(asset2.external_id), [asset["id"] for asset in response.data["results"]]
        )

        response = self.client.get(
            f"/api/v1/asset/?warranty_amc_end_of_validity_after={now().date() + timedelta(days=1)}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(
            str(asset2.external_id), [asset["id"] for asset in response.data["results"]]
        )
        self.assertNotIn(
            str(asset1.external_id), [asset["id"] for asset in response.data["results"]]
        )


class AssetConfigValidationTestCase(TestUtils, APITestCase):
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
        cls.asset_location = cls.create_asset_location(cls.facility)
        cls.user = cls.create_user("staff", cls.district, home_facility=cls.facility)

    def test_create_asset_with_unique_ip(self):
        sample_data = {
            "name": "Test Asset",
            "asset_type": 50,
            "location": self.asset_location.external_id,
            "asset_class": AssetClasses.HL7MONITOR.name,
            "meta": {"local_ip_address": "192.168.1.14"},
        }
        response = self.client.post("/api/v1/asset/", sample_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_asset_with_duplicate_ip(self):
        self.create_asset(
            self.asset_location,
            name="I was here first",
            asset_class=AssetClasses.HL7MONITOR.name,
            meta={"local_ip_address": "192.168.1.14"},
        )
        sample_data = {
            "name": "Test Asset",
            "asset_type": 50,
            "location": self.asset_location.external_id,
            "asset_class": AssetClasses.HL7MONITOR.name,
            "meta": {"local_ip_address": "192.168.1.14"},
        }
        response = self.client.post("/api/v1/asset/", sample_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("I was here first", response.json()["non_field_errors"][0])

    def test_create_asset_with_duplicate_ip_same_hostname_on_location(self):
        test_location = self.create_asset_location(
            self.facility, middleware_address=self.hostname
        )
        self.create_asset(
            test_location,
            name="I was here first",
            asset_class=AssetClasses.HL7MONITOR.name,
            meta={"local_ip_address": "192.168.1.14"},
        )
        sample_data = {
            "name": "Test Asset",
            "asset_type": 50,
            "location": test_location.external_id,
            "asset_class": AssetClasses.HL7MONITOR.name,
            "meta": {"local_ip_address": "192.168.1.14"},
        }
        response = self.client.post("/api/v1/asset/", sample_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("I was here first", response.json()["non_field_errors"][0])

    def test_create_asset_with_duplicate_ip_same_hostname_on_asset(self):
        self.create_asset(
            self.asset_location,
            name="I was here first",
            asset_class=AssetClasses.HL7MONITOR.name,
            meta={
                "local_ip_address": "192.168.1.14",
                "middleware_hostname": self.hostname,
            },
        )
        sample_data = {
            "name": "Test Asset",
            "asset_type": 50,
            "location": self.asset_location.external_id,
            "asset_class": AssetClasses.HL7MONITOR.name,
            "meta": {"local_ip_address": "192.168.1.14"},
        }
        response = self.client.post("/api/v1/asset/", sample_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("I was here first", response.json()["non_field_errors"][0])

    def test_create_asset_with_duplicate_ip_same_hostname_on_location_asset(self):
        test_location = self.create_asset_location(
            self.facility, middleware_address=self.hostname
        )
        self.create_asset(
            test_location,
            name="I was here first",
            asset_class=AssetClasses.HL7MONITOR.name,
            meta={
                "local_ip_address": "192.168.1.14",
                "middleware_hostname": self.hostname,
            },
        )
        sample_data = {
            "name": "Test Asset",
            "asset_type": 50,
            "location": test_location.external_id,
            "asset_class": AssetClasses.HL7MONITOR.name,
            "meta": {"local_ip_address": "192.168.1.14"},
        }
        response = self.client.post("/api/v1/asset/", sample_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("I was here first", response.json()["non_field_errors"][0])

    def test_create_asset_with_duplicate_ip_different_hostname_on_location(self):
        test_location = self.create_asset_location(
            self.facility, middleware_address="not-test-middleware.com"
        )
        self.create_asset(
            self.asset_location,
            name="I was here first",
            asset_class=AssetClasses.HL7MONITOR.name,
            meta={"local_ip_address": "192.168.1.14"},
        )
        sample_data = {
            "name": "Test Asset",
            "asset_type": 50,
            "location": test_location.external_id,
            "asset_class": AssetClasses.HL7MONITOR.name,
            "meta": {"local_ip_address": "192.168.1.14"},
        }
        response = self.client.post("/api/v1/asset/", sample_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_asset_with_duplicate_ip_different_hostname_on_asset(self):
        self.create_asset(
            self.asset_location,
            name="I was here first",
            asset_class=AssetClasses.HL7MONITOR.name,
            meta={"local_ip_address": "192.168.1.14"},
        )
        sample_data = {
            "name": "Test Asset",
            "asset_type": 50,
            "location": self.asset_location.external_id,
            "asset_class": AssetClasses.HL7MONITOR.name,
            "meta": {
                "local_ip_address": "192.168.1.14",
                "middleware_hostname": "not-test-middleware.com",
            },
        }
        response = self.client.post("/api/v1/asset/", sample_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_asset_with_duplicate_ip_different_hostname_on_location_asset(self):
        test_location = self.create_asset_location(
            self.facility, middleware_address="not-test-middleware.com"
        )
        self.create_asset(
            test_location,
            name="I was here first",
            asset_class=AssetClasses.HL7MONITOR.name,
            meta={
                "local_ip_address": "192.168.1.14",
                "middleware_hostname": self.hostname,
            },
        )
        sample_data = {
            "name": "Test Asset",
            "asset_type": 50,
            "location": test_location.external_id,
            "asset_class": AssetClasses.HL7MONITOR.name,
            "meta": {
                "local_ip_address": "192.168.1.14",
                "middleware_hostname": "not-test-middleware.com",
            },
        }
        response = self.client.post("/api/v1/asset/", sample_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
