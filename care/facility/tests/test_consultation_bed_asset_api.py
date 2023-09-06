from datetime import datetime

from rest_framework import status

from care.facility.models import Asset, AssetLocation, Bed, ConsultationBedAsset
from care.utils.tests.test_base import TestBase


class ConsultationBedAssetApiTestCase(TestBase):
    def setUp(self) -> None:
        super().setUp()
        self.asset_location: AssetLocation = AssetLocation.objects.create(
            name="asset location", location_type=1, facility=self.facility
        )
        self.bed1 = Bed.objects.create(
            name="bed1", location=self.asset_location, facility=self.facility
        )
        self.bed2 = Bed.objects.create(
            name="bed2", location=self.asset_location, facility=self.facility
        )
        self.asset1 = Asset.objects.create(
            name="asset1", current_location=self.asset_location
        )
        self.asset2 = Asset.objects.create(
            name="asset2", current_location=self.asset_location
        )
        self.asset3 = Asset.objects.create(
            name="asset3", current_location=self.asset_location
        )

    def test_link_asset_to_consultation_bed(self):
        consultation = self.create_consultation()
        response = self.client.post(
            "/api/v1/consultationbed/",
            {
                "consultation": consultation.external_id,
                "bed": self.bed1.external_id,
                "start_date": datetime.now().isoformat(),
                "assets": [self.asset1.external_id, self.asset2.external_id],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ConsultationBedAsset.objects.count(), 2)

    def test_link_asset_to_consultation_bed_with_asset_already_in_use(self):
        consultation = self.create_consultation()
        self.client.post(
            "/api/v1/consultationbed/",
            {
                "consultation": consultation.external_id,
                "bed": self.bed1.external_id,
                "start_date": datetime.now().isoformat(),
                "assets": [self.asset1.external_id, self.asset2.external_id],
            },
        )
        consultation2 = self.create_consultation()
        response = self.client.post(
            "/api/v1/consultationbed/",
            {
                "consultation": consultation2.external_id,
                "bed": self.bed2.external_id,
                "start_date": datetime.now().isoformat(),
                "assets": [self.asset1.external_id, self.asset3.external_id],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
