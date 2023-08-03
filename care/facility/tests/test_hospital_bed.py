from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from care.facility.tests.mixins import TestClassMixin
from care.utils.tests.test_base import TestBase


class AssetViewSetTestCase(TestBase, TestClassMixin, APITestCase):
    asset_id = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.hospital_doctor = cls.create_hospital_doctor()

    def setUp(self):
        refresh_token = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh_token.access_token}"
        )

    def test_list_assets(self):
        pass
