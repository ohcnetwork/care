from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase

from care.facility.api.viewsets.bed import BedViewSet
from care.facility.models import AssetLocation, Bed, ConsultationBed, User
from care.facility.models.patient_base import BedType
from care.facility.tests.mixins import TestClassMixin
from care.utils.tests.test_base import TestBase


class BedViewSetTestCase(TestBase, TestClassMixin, APITestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        state = self.create_state()
        self.district = self.create_district(state=state)
        self.user = self.create_user(district=self.district, username="test user")
        self.facility = self.create_facility(district=self.district, user=self.user)
        self.asset_location = AssetLocation.objects.create(
            name="asset1 location", location_type=1, facility=self.facility
        )
        self.bed = Bed.objects.create(
            name="Test Bed", facility=self.facility, location=self.asset_location
        )

    def test_list_beds(self):
        response = self.new_request(
            ("/api/v1/bed/",),
            {"get": "list"},
            BedViewSet,
            self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, self.bed.external_id)

    def test_retrieve_bed(self):
        response = self.new_request(
            ("/api/v1/bed/{self.bed.external_id}/",),
            {"get": "retrieve"},
            BedViewSet,
            self.user,
            {"external_id": self.bed.external_id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], self.bed.name)

    def test_create_bed(self):
        sample_data = {
            "name": "New Test Bed",
            "facility": self.facility.external_id,
            "location": self.asset_location.external_id,
            "bed_type": BedType.REGULAR.value,
        }
        response = self.new_request(
            ("/api/v1/bed/", sample_data, "json"),
            {"post": "create"},
            BedViewSet,
            self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], sample_data["name"])

    def test_update_bed(self):
        sample_data = {
            "name": "Updated Test Bed",
            "facility": self.facility.external_id,
            "location": self.asset_location.external_id,
        }
        response = self.new_request(
            (f"/api/v1/bed/{self.bed.external_id}/", sample_data, "json"),
            {"patch": "partial_update"},
            BedViewSet,
            self.user,
            {"external_id": self.bed.external_id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], sample_data["name"])

    def test_delete_bed_as_non_district_lab_admin(self):
        response = self.new_request(
            (f"/api/v1/bed/{self.bed.external_id}/",),
            {"delete": "destroy"},
            BedViewSet,
            self.user,
            {"external_id": self.bed.external_id},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_bed_as_district_lab_admin(self):
        self.user.user_type = User.TYPE_VALUE_MAP["DistrictLabAdmin"]
        self.user.save()
        response = self.new_request(
            (f"/api/v1/bed/{self.bed.external_id}/",),
            {"delete": "destroy"},
            BedViewSet,
            self.user,
            {"external_id": self.bed.external_id},
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_occupied_bed_as_district_lab_admin(self):
        self.user.user_type = User.TYPE_VALUE_MAP["DistrictLabAdmin"]
        self.user.save()
        patient = self.create_patient()
        consultation = self.create_consultation(patient=patient, facility=self.facility)
        ConsultationBed.objects.create(
            consultation=consultation, bed=self.bed, start_date=timezone.now()
        )
        response = self.new_request(
            (f"/api/v1/bed/{self.bed.external_id}/",),
            {"delete": "destroy"},
            BedViewSet,
            self.user,
            {"external_id": self.bed.external_id},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data[0], "Bed is occupied. Please discharge the patient first"
        )
