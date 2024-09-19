from django.db import IntegrityError
from rest_framework.test import APITestCase

from care.users.models import UserFlag
from care.utils.registries.feature_flag import FlagRegistry, FlagType
from care.utils.tests.test_utils import TestUtils


class UserFlagsTestCase(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls):
        FlagRegistry.register(FlagType.USER, "TEST_FLAG")
        FlagRegistry.register(FlagType.USER, "TEST_FLAG_2")
        cls.district = cls.create_district(cls.create_state())

    def setUp(self) -> None:
        self.user = self.create_user("user", self.district)
        super().setUp()

    def test_user_flags(self):
        UserFlag.objects.create(user=self.user, flag="TEST_FLAG")
        self.assertTrue(UserFlag.check_user_has_flag(self.user.id, "TEST_FLAG"))

    def test_user_flags_negative(self):
        self.assertFalse(UserFlag.check_user_has_flag(self.user.id, "TEST_FLAG"))

    def test_create_duplicate_flag(self):
        UserFlag.objects.create(user=self.user, flag="TEST_FLAG")
        with self.assertRaises(IntegrityError):
            UserFlag.objects.create(user=self.user, flag="TEST_FLAG")

    def test_get_all_flags(self):
        UserFlag.objects.create(user=self.user, flag="TEST_FLAG")
        UserFlag.objects.create(user=self.user, flag="TEST_FLAG_2")
        self.assertEqual(
            UserFlag.get_all_flags(self.user.id), ("TEST_FLAG", "TEST_FLAG_2")
        )

    def test_get_user_flags_api(self):
        UserFlag.objects.create(user=self.user, flag="TEST_FLAG")
        UserFlag.objects.create(user=self.user, flag="TEST_FLAG_2")
        response = self.client.get("/api/v1/users/getcurrentuser/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user_flags"], ["TEST_FLAG", "TEST_FLAG_2"])
