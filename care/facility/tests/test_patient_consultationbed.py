import datetime

from django.utils.timezone import make_aware
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase

from care.facility.api.viewsets.bed import ConsultationBedViewSet
from care.facility.models import FacilityUser
from care.facility.models.asset import AssetLocation
from care.facility.models.bed import Bed, ConsultationBed
from care.facility.tests.mixins import TestClassMixin
from care.users.models import User
from care.utils.tests.test_base import TestBase


class TestPatientConsultationbed(TestBase, TestClassMixin, APITestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.location = AssetLocation.objects.create(
            name="asset location", location_type=1, facility=self.facility
        )
        self.bed: Bed = Bed.objects.create(
            name="Test Bed",
            facility=self.facility,
            location=self.location,
        )
        self.consultation = self.create_consultation()

    def test_patient_privacy_toggle_success(self):
        allowed_user_types = [
            "DistrictAdmin",
            "WardAdmin",
            "LocalBodyAdmin",
            "StateAdmin",
            "Doctor",
            "Staff",
        ]
        for user_type in allowed_user_types:
            self.user = self.create_user(
                username=f"{user_type} test user",
                user_type=User.TYPE_VALUE_MAP[user_type],
                district=self.district,
                home_facility=self.facility,
            )
            self.facility_user = FacilityUser.objects.create(
                created_by=self.user, facility=self.facility, user=self.user
            )
            consultation_bed: ConsultationBed = ConsultationBed.objects.create(
                consultation=self.consultation,
                bed=self.bed,
                start_date=make_aware(datetime.datetime.now()),
                end_date=make_aware(datetime.datetime.now()),
                privacy=True,
            )

            response = self.new_request(
                (
                    f"/api/v1/consultationbed/{consultation_bed.external_id}/toggle_patient_privacy/",
                    {},
                    "json",
                ),
                {"patch": "toggle_patient_privacy"},
                ConsultationBedViewSet,
                self.user,
                {"external_id": consultation_bed.external_id},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            consultation_bed.delete()
            self.consultation.delete()
            self.bed.delete()
            self.location.delete()
            self.facility.delete()
            self.user.delete()

    def test_patient_privacy_toggle_failure(self):
        non_allowed_user_types = [
            "Transportation",
            "Pharmacist",
            "Volunteer",
            "StaffReadOnly",
            "Reserved",
            "DistrictLabAdmin",
            "DistrictReadOnlyAdmin",
            "StateLabAdmin",
            "StateReadOnlyAdmin",
            "Doctor",
            "Staff",
        ]
        for user_type in non_allowed_user_types:
            self.facility2 = self.create_facility(self.district, name="Test Facility 2")
            self.user = self.create_user(
                username=f"{user_type} test user",
                user_type=User.TYPE_VALUE_MAP[user_type],
                district=self.district,
                home_facility=self.facility2,
            )
            self.facility_user = FacilityUser.objects.create(
                created_by=self.user, facility=self.facility, user=self.user
            )

            consultation_bed: ConsultationBed = ConsultationBed.objects.create(
                consultation=self.consultation,
                bed=self.bed,
                start_date=make_aware(datetime.datetime.now()),
                end_date=make_aware(datetime.datetime.now()),
                privacy=True,
            )

            response = self.new_request(
                (
                    f"/api/v1/consultationbed/{consultation_bed.external_id}/toggle_patient_privacy/",
                    {},
                    "json",
                ),
                {"patch": "toggle_patient_privacy"},
                ConsultationBedViewSet,
                self.user,
                {"external_id": consultation_bed.external_id},
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            consultation_bed.delete()
            self.consultation.delete()
            self.bed.delete()
            self.location.delete()
            self.facility.delete()
            self.user.delete()
