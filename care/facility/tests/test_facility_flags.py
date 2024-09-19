from django.db import IntegrityError
from rest_framework.test import APITestCase

from care.facility.models.facility_flag import FacilityFlag
from care.utils.registries.feature_flag import FlagRegistry, FlagType
from care.utils.tests.test_utils import TestUtils


class FacilityFlagsTestCase(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls):
        FlagRegistry.register(FlagType.FACILITY, "TEST_FLAG")
        FlagRegistry.register(FlagType.FACILITY, "TEST_FLAG_2")
        cls.district = cls.create_district(cls.create_state())
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)

    def setUp(self) -> None:
        self.facility = self.create_facility(
            self.super_user, self.district, self.local_body
        )

    def test_facility_flags(self):
        FacilityFlag.objects.create(facility=self.facility, flag="TEST_FLAG")
        self.assertTrue(
            FacilityFlag.check_facility_has_flag(self.facility.id, "TEST_FLAG")
        )

    def test_facility_flags_negative(self):
        self.assertFalse(
            FacilityFlag.check_facility_has_flag(self.facility.id, "TEST_FLAG")
        )

    def test_create_duplicate_flag(self):
        FacilityFlag.objects.create(facility=self.facility, flag="TEST_FLAG")
        with self.assertRaises(IntegrityError):
            FacilityFlag.objects.create(facility=self.facility, flag="TEST_FLAG")

    def test_get_all_flags(self):
        FacilityFlag.objects.create(facility=self.facility, flag="TEST_FLAG")
        FacilityFlag.objects.create(facility=self.facility, flag="TEST_FLAG_2")
        self.assertEqual(
            FacilityFlag.get_all_flags(self.facility.id), ("TEST_FLAG", "TEST_FLAG_2")
        )

    def test_get_user_flags_api(self):
        FacilityFlag.objects.create(facility=self.facility, flag="TEST_FLAG")
        FacilityFlag.objects.create(facility=self.facility, flag="TEST_FLAG_2")
        user = self.create_user("user", self.district, home_facility=self.facility)
        self.client.force_authenticate(user=user)
        response = self.client.get(f"/api/v1/facility/{self.facility.external_id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["facility_flags"], ["TEST_FLAG", "TEST_FLAG_2"]
        )
