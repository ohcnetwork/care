from datetime import datetime, timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from care.facility.models import Asset, Bed, ConsultationBedAsset
from care.facility.models.bed import ConsultationBed
from care.utils.tests.test_utils import TestUtils


class ConsultationBedApiTestCase(TestUtils, APITestCase):
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
        cls.state_admin = cls.create_user(
            "state_admin", cls.district, state=cls.state, user_type=40
        )
        cls.patient = cls.create_patient(
            cls.district, cls.facility, local_body=cls.local_body
        )

    def setUp(self) -> None:
        super().setUp()
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
        self.consultation = self.create_consultation(self.patient, self.facility)

    def test_missing_fields(self):
        consultation_bed = ConsultationBed.objects.create(
            consultation=self.consultation,
            bed=self.bed1,
            start_date=timezone.now(),
        )
        response = self.client.patch(
            f"/api/v1/consultationbed/{consultation_bed.external_id}/",
            {
                "consultation": self.consultation.external_id,
                "bed": self.bed1.external_id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"start_date": ["This field is required."]},
        )

        response = self.client.patch(
            f"/api/v1/consultationbed/{consultation_bed.external_id}/",
            {
                "consultation": self.consultation.external_id,
                "start_date": timezone.now(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"bed": ["This field is required."]},
        )

        response = self.client.patch(
            f"/api/v1/consultationbed/{consultation_bed.external_id}/",
            {
                "bed": self.bed1.external_id,
                "start_date": timezone.now(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"consultation": ["This field is required."]},
        )

    def test_no_access_to_facility(self):
        user2 = self.create_user(username="user2", district=self.district)
        self.client.force_authenticate(user2)
        response = self.client.post(
            "/api/v1/consultationbed/",
            {
                "consultation": self.consultation.external_id,
                "bed": self.bed1.external_id,
                "start_date": timezone.now(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"non_field_errors": ["You do not have access to this facility"]},
        )

    def test_patient_not_active(self):
        err = {"non_field_errors": ["Patient not active"]}
        patient = self.create_patient(self.district, self.facility)
        self.consultation.discharge_date = timezone.now()
        self.consultation.save()
        response = self.client.post(
            "/api/v1/consultationbed/",
            {
                "consultation": self.consultation.external_id,
                "bed": self.bed1.external_id,
                "start_date": timezone.now(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), err)

        consultation2 = self.create_consultation(
            patient, self.facility, death_datetime=timezone.now()
        )
        response = self.client.post(
            "/api/v1/consultationbed/",
            {
                "consultation": consultation2.external_id,
                "bed": self.bed1.external_id,
                "start_date": timezone.now(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), err)

        patient.is_active = False
        patient.save()
        consultation3 = self.create_consultation(patient, self.facility)
        response = self.client.post(
            "/api/v1/consultationbed/",
            {
                "consultation": consultation3.external_id,
                "bed": self.bed1.external_id,
                "start_date": timezone.now(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), err)

    def test_bed_in_different_facility(self):
        facility2 = self.create_facility(
            self.super_user, self.district, self.local_body
        )
        asset_location2 = self.create_asset_location(facility2)
        bed2 = Bed.objects.create(
            name="bed1", location=asset_location2, facility=facility2
        )
        self.client.force_authenticate(self.state_admin)
        response = self.client.post(
            "/api/v1/consultationbed/",
            {
                "consultation": self.consultation.external_id,
                "bed": bed2.external_id,
                "start_date": timezone.now(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"non_field_errors": ["Consultation and bed are not in the same facility"]},
        )

    def test_bed_already_in_use(self):
        self.client.post(
            "/api/v1/consultationbed/",
            {
                "consultation": self.consultation.external_id,
                "bed": self.bed1.external_id,
                "start_date": timezone.now(),
            },
        )

        patient2 = self.create_patient(self.district, self.facility)
        consultation2 = self.create_consultation(patient2, self.facility)
        response = self.client.post(
            "/api/v1/consultationbed/",
            {
                "consultation": consultation2.external_id,
                "bed": self.bed1.external_id,
                "start_date": timezone.now(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"non_field_errors": ["Bed is already in use"]},
        )

    def test_same_set_of_bed_and_assets_assigned(self):
        self.client.post(
            "/api/v1/consultationbed/",
            {
                "consultation": self.consultation.external_id,
                "bed": self.bed1.external_id,
                "start_date": timezone.now(),
                "assets": [self.asset1.external_id, self.asset2.external_id],
            },
        )
        response = self.client.post(
            "/api/v1/consultationbed/",
            {
                "consultation": self.consultation.external_id,
                "bed": self.bed1.external_id,
                "start_date": timezone.now(),
                "assets": [self.asset1.external_id, self.asset2.external_id],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"non_field_errors": ["These set of bed and assets are already assigned"]},
        )

    def test_start_date_before_end_date(self):
        response = self.client.post(
            "/api/v1/consultationbed/",
            {
                "consultation": self.consultation.external_id,
                "bed": self.bed1.external_id,
                "start_date": timezone.now(),
                "end_date": timezone.now() - timedelta(days=1),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"end_date": ["End date cannot be before the start date"]},
        )

    def test_start_date_before_consultation_encounter_date(self):
        self.consultation.encounter_date = timezone.now()
        self.consultation.save()
        response = self.client.post(
            "/api/v1/consultationbed/",
            {
                "consultation": self.consultation.external_id,
                "bed": self.bed1.external_id,
                "start_date": timezone.now() - timedelta(days=1),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"start_date": ["Start date cannot be before the admission date"]},
        )

    def test_start_date_before_previous_bed_start_date(self):
        self.client.post(
            "/api/v1/consultationbed/",
            {
                "consultation": self.consultation.external_id,
                "bed": self.bed1.external_id,
                "start_date": timezone.now(),
            },
        )
        response = self.client.post(
            "/api/v1/consultationbed/",
            {
                "consultation": self.consultation.external_id,
                "bed": self.bed2.external_id,
                "start_date": timezone.now() - timedelta(days=1),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"start_date": ["Start date cannot be before previous bed start date"]},
        )

    def test_overlap_caused_by_setting_current_bed_end_date_from_current_start_date(
        self,
    ):
        self.client.post(
            "/api/v1/consultationbed/",
            {
                "consultation": self.consultation.external_id,
                "bed": self.bed1.external_id,
                "start_date": timezone.now(),
                "end_date": timezone.now() + timedelta(days=1),
            },
        )

        consultation2 = self.create_consultation(self.patient, self.facility)
        self.client.post(
            "/api/v1/consultationbed/",
            {
                "consultation": consultation2.external_id,
                "bed": self.bed1.external_id,
                "start_date": timezone.now() - timedelta(days=2),
            },
        )
        response = self.client.post(
            "/api/v1/consultationbed/",
            {
                "consultation": consultation2.external_id,
                "bed": self.bed2.external_id,
                "start_date": timezone.now(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"start_date": ["Cannot create conflicting entry"]},
        )

    def test_consultation_bed_conflicting_shift(self):
        ConsultationBed.objects.create(
            consultation=self.consultation,
            bed=self.bed1,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=1),
        )

        patient2 = self.create_patient(self.district, self.facility)
        consultation2 = self.create_consultation(patient2, self.facility)
        response = self.client.post(
            "/api/v1/consultationbed/",
            {
                "consultation": consultation2.external_id,
                "bed": self.bed1.external_id,
                "start_date": timezone.now(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"start_date": ["Cannot create conflicting entry"]},
        )

    def test_consultation_bed_conflicting_shift_with_end_date(self):
        ConsultationBed.objects.create(
            consultation=self.consultation,
            bed=self.bed1,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=1),
        )

        patient2 = self.create_patient(self.district, self.facility)
        consultation2 = self.create_consultation(patient2, self.facility)
        response = self.client.post(
            "/api/v1/consultationbed/",
            {
                "consultation": consultation2.external_id,
                "bed": self.bed1.external_id,
                "start_date": timezone.now() - timedelta(days=1),
                "end_date": timezone.now(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"end_date": ["Cannot create conflicting entry"]},
        )

    def test_update_end_date(self):
        start_time = timezone.now()
        end_time = timezone.now() + timedelta(seconds=10)
        response = self.client.post(
            "/api/v1/consultationbed/",
            {
                "consultation": self.consultation.external_id,
                "bed": self.bed1.external_id,
                "start_date": start_time,
            },
        )
        response = self.client.patch(
            f"/api/v1/consultationbed/{response.json()['id']}/",
            {
                "consultation": self.consultation.external_id,
                "bed": self.bed1.external_id,
                "start_date": start_time,
                "end_date": end_time,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            datetime.strptime(response.json()["end_date"], "%Y-%m-%dT%H:%M:%S.%f%z"),
            end_time,
        )

    def test_link_asset_to_consultation_bed(self):
        response = self.client.post(
            "/api/v1/consultationbed/",
            {
                "consultation": self.consultation.external_id,
                "bed": self.bed1.external_id,
                "start_date": timezone.now(),
                "assets": [self.asset1.external_id, self.asset2.external_id],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ConsultationBedAsset.objects.count(), 2)

    def test_link_asset_to_consultation_bed_with_asset_already_in_use(self):
        self.client.post(
            "/api/v1/consultationbed/",
            {
                "consultation": self.consultation.external_id,
                "bed": self.bed1.external_id,
                "start_date": timezone.now(),
                "assets": [self.asset1.external_id, self.asset2.external_id],
            },
        )
        consultation2 = self.create_consultation(self.patient, self.facility)
        response = self.client.post(
            "/api/v1/consultationbed/",
            {
                "consultation": consultation2.external_id,
                "bed": self.bed2.external_id,
                "start_date": timezone.now(),
                "assets": [self.asset1.external_id, self.asset3.external_id],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
