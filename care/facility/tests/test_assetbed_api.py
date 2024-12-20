from rest_framework import status
from rest_framework.test import APITestCase

from care.facility.models import AssetBed, Bed
from care.users.models import User
from care.utils.assetintegration.asset_classes import AssetClasses
from care.utils.tests.test_utils import TestUtils


class AssetBedViewSetTests(TestUtils, APITestCase):
    """
    Test class for AssetBed
    """

    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.facility2 = cls.create_facility(
            cls.super_user, cls.district, cls.local_body
        )
        cls.user = cls.create_user(
            "user",
            district=cls.district,
            local_body=cls.local_body,
            home_facility=cls.facility,
        )  # user from facility
        cls.foreign_user = cls.create_user(
            "foreign_user",
            district=cls.district,
            local_body=cls.local_body,
            home_facility=cls.facility2,
        )  # user outside the facility
        cls.patient = cls.create_patient(
            cls.district, cls.facility, local_body=cls.local_body
        )
        cls.asset_location1 = cls.create_asset_location(cls.facility)
        cls.asset1 = cls.create_asset(
            cls.asset_location1, asset_class=AssetClasses.HL7MONITOR.name
        )
        cls.bed1 = Bed.objects.create(
            name="bed1", location=cls.asset_location1, facility=cls.facility
        )
        cls.asset_location2 = cls.create_asset_location(cls.facility)
        # camera asset
        cls.asset2 = cls.create_asset(
            cls.asset_location2, asset_class=AssetClasses.ONVIF.name
        )
        cls.bed2 = Bed.objects.create(
            name="bed2", location=cls.asset_location2, facility=cls.facility
        )
        cls.asset_location3 = cls.create_asset_location(cls.facility)
        cls.asset3 = cls.create_asset(
            cls.asset_location3, asset_class=AssetClasses.VENTILATOR.name
        )
        cls.bed3 = Bed.objects.create(
            name="bed3", location=cls.asset_location3, facility=cls.facility
        )
        # for testing create, put and patch requests
        cls.bed4 = Bed.objects.create(
            name="bed4", location=cls.asset_location3, facility=cls.facility
        )
        cls.foreign_asset_location = cls.create_asset_location(cls.facility2)
        cls.foreign_asset = cls.create_asset(cls.foreign_asset_location)
        cls.foreign_bed = Bed.objects.create(
            name="foreign_bed",
            location=cls.foreign_asset_location,
            facility=cls.facility2,
        )

        cls.create_assetbed(bed=cls.bed2, asset=cls.asset2)
        cls.create_assetbed(bed=cls.bed3, asset=cls.asset3)

        # assetbed for different facility
        cls.create_assetbed(bed=cls.foreign_bed, asset=cls.foreign_asset)

    def setUp(self) -> None:
        super().setUp()
        self.assetbed = self.create_assetbed(bed=self.bed1, asset=self.asset1)

    def get_base_url(self) -> str:
        return "/api/v1/assetbed"

    def get_url(self, external_id=None):
        """
        Constructs the url for ambulance api
        """
        base_url = f"{self.get_base_url()}/"
        if external_id is not None:
            base_url += f"{external_id}/"
        return base_url

    def test_list_assetbed(self):
        # assetbed accessible to facility 1 user (current user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 3)

        # logging in as foreign user
        self.client.force_login(self.foreign_user)

        # assetbed accessible to facility 2 user (foreign user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

        # logging in as superuser
        self.client.force_login(self.super_user)

        # access to all assetbed
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], AssetBed.objects.count())

        # testing for filters
        response = self.client.get(self.get_url(), {"asset": self.asset1.external_id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["count"], AssetBed.objects.filter(asset=self.asset1).count()
        )

        response = self.client.get(self.get_url(), {"bed": self.bed1.external_id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["count"], AssetBed.objects.filter(bed=self.bed1).count()
        )
        self.assertEqual(
            response.data["results"][0]["bed_object"]["name"], self.bed1.name
        )

        response = self.client.get(
            self.get_url(), {"facility": self.facility.external_id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["count"],
            AssetBed.objects.filter(bed__facility=self.facility).count(),
        )

    def test_create_assetbed(self):
        # Missing asset and bed
        missing_fields_data = {}
        response = self.client.post(self.get_url(), missing_fields_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("asset", response.data)
        self.assertIn("bed", response.data)

        # Invalid asset UUID
        invalid_asset_uuid_data = {
            "asset": "invalid-uuid",
            "bed": str(self.bed1.external_id),
        }
        response = self.client.post(
            self.get_url(), invalid_asset_uuid_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("asset", response.data)

        # Invalid bed UUID
        invalid_bed_uuid_data = {
            "asset": str(self.asset1.external_id),
            "bed": "invalid-uuid",
        }
        response = self.client.post(
            self.get_url(), invalid_bed_uuid_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("bed", response.data)

        # Non-existent asset UUID
        non_existent_asset_uuid_data = {
            "asset": "11111111-1111-1111-1111-111111111111",
            "bed": str(self.bed1.external_id),
        }
        response = self.client.post(
            self.get_url(), non_existent_asset_uuid_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Non-existent bed UUID
        non_existent_bed_uuid_data = {
            "asset": str(self.asset1.external_id),
            "bed": "11111111-1111-1111-1111-111111111111",
        }
        response = self.client.post(
            self.get_url(), non_existent_bed_uuid_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # User does not have access to foreign facility
        foreign_user_data = {
            "asset": str(self.foreign_asset.external_id),
            "bed": str(self.foreign_bed.external_id),
        }
        self.client.force_login(self.user)  # Ensure current user is logged in
        response = self.client.post(self.get_url(), foreign_user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Invalid asset class (e.g., VENTILATOR)
        invalid_asset_class_data = {
            "asset": str(self.asset3.external_id),  # VENTILATOR asset class
            "bed": str(self.bed1.external_id),
        }
        response = self.client.post(
            self.get_url(), invalid_asset_class_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("asset", response.data)

        # Asset and bed in different facilities
        asset_bed_different_facilities = {
            "asset": str(self.foreign_asset.external_id),
            "bed": str(self.bed1.external_id),
        }
        response = self.client.post(
            self.get_url(), asset_bed_different_facilities, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Trying to create a duplicate assetbed with bed2 and asset2 (assetbed already exist with same bed and asset)
        duplicate_asset_class_data = {
            "asset": str(self.asset2.external_id),  # asset2 is already assigned to bed2
            "bed": str(self.bed2.external_id),
        }
        response = self.client.post(
            self.get_url(), duplicate_asset_class_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Successfully create AssetBed with valid data
        valid_data = {
            "asset": str(self.asset1.external_id),
            "bed": str(self.bed4.external_id),
        }
        response = self.client.post(self.get_url(), valid_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_retrieve_assetbed(self):
        response = self.client.get(self.get_url(external_id=self.assetbed.external_id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["asset_object"]["id"], str(self.assetbed.asset.external_id)
        )
        self.assertEqual(
            response.data["bed_object"]["id"], str(self.assetbed.bed.external_id)
        )

    def test_update_assetbed(self):
        # checking old values
        response = self.client.get(self.get_url(external_id=self.assetbed.external_id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["meta"], {})
        self.assertEqual(
            response.data["asset_object"]["id"], str(self.assetbed.asset.external_id)
        )
        self.assertEqual(
            response.data["bed_object"]["id"], str(self.assetbed.bed.external_id)
        )

        invalid_updated_data = {
            "asset": self.asset2.external_id,
            "meta": {"sample_data": "sample value"},
        }
        response = self.client.put(
            self.get_url(external_id=self.assetbed.external_id),
            invalid_updated_data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        invalid_updated_data = {
            "bed": self.bed2.external_id,
            "meta": {"sample_data": "sample value"},
        }
        response = self.client.put(
            self.get_url(external_id=self.assetbed.external_id),
            invalid_updated_data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        updated_data = {
            "bed": self.bed4.external_id,
            "asset": self.asset2.external_id,
            "meta": {"sample_data": "sample value"},
        }
        response = self.client.put(
            self.get_url(external_id=self.assetbed.external_id),
            updated_data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assetbed.refresh_from_db()

        self.assertEqual(self.assetbed.bed.external_id, self.bed4.external_id)
        self.assertEqual(self.assetbed.asset.external_id, self.asset2.external_id)
        self.assertEqual(self.assetbed.meta, {"sample_data": "sample value"})

    def test_patch_assetbed(self):
        # checking old values
        response = self.client.get(self.get_url(external_id=self.assetbed.external_id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["meta"], {})
        self.assertEqual(
            response.data["asset_object"]["id"], str(self.assetbed.asset.external_id)
        )
        self.assertEqual(
            response.data["bed_object"]["id"], str(self.assetbed.bed.external_id)
        )

        invalid_updated_data = {
            "asset": self.asset2.external_id,
            "meta": {"sample_data": "sample value"},
        }
        response = self.client.patch(
            self.get_url(external_id=self.assetbed.external_id),
            invalid_updated_data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        invalid_updated_data = {
            "bed": self.bed4.external_id,
            "meta": {"sample_data": "sample value"},
        }
        response = self.client.patch(
            self.get_url(external_id=self.assetbed.external_id),
            invalid_updated_data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        updated_data = {
            "bed": self.bed4.external_id,
            "asset": self.asset2.external_id,
        }

        response = self.client.patch(
            self.get_url(external_id=self.assetbed.external_id),
            updated_data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assetbed.refresh_from_db()

        self.assertEqual(self.assetbed.bed.external_id, self.bed4.external_id)
        self.assertEqual(self.assetbed.asset.external_id, self.asset2.external_id)

    def test_delete_assetbed(self):
        # confirming that the object exist
        response = self.client.get(self.get_url(external_id=self.assetbed.external_id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.delete(
            self.get_url(external_id=self.assetbed.external_id)
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # confirming if it's deleted
        response = self.client.get(self.get_url(external_id=self.assetbed.external_id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # confirming using db
        self.assetbed.refresh_from_db()
        self.assertFalse(
            AssetBed.objects.filter(external_id=self.assetbed.external_id).exists()
        )

    def test_linking_multiple_cameras_to_a_bed(self):
        # We already have camera linked(asset2) to bed2
        # Attempt linking another camera to same bed.
        new_camera_asset = self.create_asset(
            self.asset_location2, asset_class=AssetClasses.ONVIF.name
        )
        data = {
            "bed": self.bed2.external_id,
            "asset": new_camera_asset.external_id,
        }
        res = self.client.post(self.get_url(), data, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_linking_multiple_hl7_monitors_to_a_bed(self):
        # We already have hl7 monitor linked(asset1) to bed1)
        # Attempt linking another hl7 monitor to same bed.
        new_hl7_monitor_asset = self.create_asset(
            self.asset_location2, asset_class=AssetClasses.HL7MONITOR.name
        )
        data = {
            "bed": self.bed1.external_id,
            "asset": new_hl7_monitor_asset.external_id,
        }
        res = self.client.post("/api/v1/assetbed/", data, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class AssetBedCameraPresetViewSetTestCase(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.user = cls.create_user(
            User.TYPE_VALUE_MAP["DistrictAdmin"],
            cls.district,
            home_facility=cls.facility,
        )
        cls.asset_location = cls.create_asset_location(cls.facility)
        cls.asset1 = cls.create_asset(
            cls.asset_location, asset_class=AssetClasses.ONVIF.name
        )
        cls.asset2 = cls.create_asset(
            cls.asset_location, asset_class=AssetClasses.ONVIF.name
        )
        cls.bed = cls.create_bed(cls.facility, cls.asset_location)
        cls.asset_bed1 = cls.create_assetbed(cls.bed, cls.asset1)
        cls.asset_bed2 = cls.create_assetbed(cls.bed, cls.asset2)

    def get_base_url(self, asset_bed_id=None):
        return f"/api/v1/assetbed/{asset_bed_id or self.asset_bed1.external_id}/camera_presets/"

    def test_list_bed_with_deleted_assetbed(self):
        res = self.client.post(
            self.get_base_url(self.asset_bed1.external_id),
            {
                "name": "Preset with proper position",
                "position": {
                    "x": 1.0,
                    "y": 1.0,
                    "zoom": 1.0,
                },
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        res = self.client.post(
            self.get_base_url(self.asset_bed2.external_id),
            {
                "name": "Preset with proper position 2",
                "position": {
                    "x": 1.0,
                    "y": 1.0,
                    "zoom": 1.0,
                },
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        res = self.client.get(f"/api/v1/bed/{self.bed.external_id}/camera_presets/")
        self.assertEqual(len(res.json()["results"]), 2)

        self.asset_bed1.delete()
        self.asset_bed1.refresh_from_db()
        res = self.client.get(f"/api/v1/bed/{self.bed.external_id}/camera_presets/")
        self.assertEqual(len(res.json()["results"]), 1)

    def test_create_camera_preset_without_position(self):
        res = self.client.post(
            self.get_base_url(),
            {
                "name": "Preset without position",
                "position": {},
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_camera_preset_with_missing_required_keys_in_position(self):
        res = self.client.post(
            self.get_base_url(),
            {
                "name": "Preset with invalid position",
                "position": {"key": "value"},
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_camera_preset_with_position_not_number(self):
        res = self.client.post(
            self.get_base_url(),
            {
                "name": "Preset with invalid position",
                "position": {
                    "x": "not a number",
                    "y": 1,
                    "zoom": 1,
                },
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_camera_preset_with_position_values_as_string(self):
        res = self.client.post(
            self.get_base_url(),
            {
                "name": "Preset with invalid position",
                "position": {
                    "x": "1",
                    "y": "1",
                    "zoom": "1",
                },
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_camera_preset_and_presence_in_various_preset_list_apis(self):
        asset_bed = self.asset_bed1
        res = self.client.post(
            self.get_base_url(asset_bed.external_id),
            {
                "name": "Preset with proper position",
                "position": {
                    "x": 1.0,
                    "y": 1.0,
                    "zoom": 1.0,
                },
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        preset_external_id = res.data["id"]

        # Check if preset in asset-bed preset list
        res = self.client.get(self.get_base_url(asset_bed.external_id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertContains(res, preset_external_id)

        # Check if preset in asset preset list
        res = self.client.get(
            f"/api/v1/asset/{asset_bed.asset.external_id}/camera_presets/"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertContains(res, preset_external_id)

        # Check if preset in bed preset list
        res = self.client.get(
            f"/api/v1/bed/{asset_bed.bed.external_id}/camera_presets/"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertContains(res, preset_external_id)

    def test_create_camera_preset_with_same_name_in_same_bed(self):
        data = {
            "name": "Duplicate Preset Name",
            "position": {
                "x": 1.0,
                "y": 1.0,
                "zoom": 1.0,
            },
        }
        self.client.post(
            self.get_base_url(self.asset_bed1.external_id), data, format="json"
        )
        res = self.client.post(
            self.get_base_url(self.asset_bed2.external_id), data, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
