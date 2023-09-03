from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from care.facility.models import Asset, Bed, ConsultationBedAsset
from care.utils.tests.test_utils import TestUtils


class ConsultationBedAssetApiTestCase(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.asset_location = cls.create_asset_location(cls.facility)
        cls.asset = cls.create_asset(cls.asset_location)
        cls.user = cls.create_user("staff", cls.district, home_facility=cls.facility)
        cls.patient = cls.create_patient(
            cls.district,
            cls.facility,
            local_body=cls.local_body,
        )

    def setUp(self) -> None:
        super().setUp()
        self.bed1 = Bed.objects.create(
            name="bed1",
            location=self.asset_location,
            facility=self.facility,
        )
        self.bed2 = Bed.objects.create(
            name="bed2",
            location=self.asset_location,
            facility=self.facility,
        )
        self.asset1 = Asset.objects.create(
            name="asset1",
            current_location=self.asset_location,
        )
        self.asset2 = Asset.objects.create(
            name="asset2",
            current_location=self.asset_location,
        )
        self.asset3 = Asset.objects.create(
            name="asset3",
            current_location=self.asset_location,
        )

    def test_link_asset_to_consultation_bed(self):
        consultation = self.create_consultation(self.patient, self.facility)
        response = self.client.post(
            "/api/v1/consultationbed/",
            {
                "consultation": consultation.external_id,
                "bed": self.bed1.external_id,
                "start_date": timezone.now().isoformat(),
                "assets": [self.asset1.external_id, self.asset2.external_id],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ConsultationBedAsset.objects.count(), 2)

    def test_link_asset_to_consultation_bed_with_asset_already_in_use(self):
        consultation = self.create_consultation(self.patient, self.facility)
        self.client.post(
            "/api/v1/consultationbed/",
            {
                "consultation": consultation.external_id,
                "bed": self.bed1.external_id,
                "start_date": timezone.now().isoformat(),
                "assets": [self.asset1.external_id, self.asset2.external_id],
            },
        )
        consultation2 = self.create_consultation(self.patient, self.facility)
        response = self.client.post(
            "/api/v1/consultationbed/",
            {
                "consultation": consultation2.external_id,
                "bed": self.bed2.external_id,
                "start_date": timezone.now().isoformat(),
                "assets": [self.asset1.external_id, self.asset3.external_id],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
