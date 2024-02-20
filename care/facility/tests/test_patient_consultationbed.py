import datetime

from django.utils.timezone import make_aware
from rest_framework import status
from rest_framework.test import APITestCase

from care.users.models import User
from care.utils.tests.test_utils import TestUtils


class TestPatientConsultationbed(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.state = cls.create_state()
        cls.district = cls.create_district(state=cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.user = cls.create_super_user(district=cls.district, username="test user")
        cls.facility = cls.create_facility(
            district=cls.district, local_body=cls.local_body, user=cls.user
        )
        cls.patient = cls.create_patient(cls.district, cls.facility)
        cls.location = cls.create_asset_location(facility=cls.facility)
        cls.bed = cls.create_bed(
            name="Test Bed",
            facility=cls.facility,
            location=cls.location,
        )
        cls.consultation = cls.create_consultation(
            facility=cls.facility, patient=cls.patient
        )

    def test_patient_privacy_toggle_success(self):
        allowed_user_types = [
            "DistrictAdmin",
            # "WardAdmin",
            # "LocalBodyAdmin",
            # "StateAdmin",
            # "Doctor",
            # "Staff",
        ]
        for user_type in allowed_user_types:
            self.user = self.create_user(
                username=f"{user_type} test user",
                user_type=User.TYPE_VALUE_MAP[user_type],
                district=self.district,
                home_facility=self.facility,
            )
            consultation_bed = self.create_consultation_bed(
                consultation=self.consultation,
                bed=self.bed,
                start_date=make_aware(datetime.datetime.now()),
                end_date=make_aware(datetime.datetime.now()),
                privacy=False,
            )

            self.client.force_authenticate(user=self.user)
            response = self.client.post(
                f"/api/v1/consultationbed/{consultation_bed.external_id}/patient_privacy/",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            response = self.client.delete(
                f"/api/v1/consultationbed/{consultation_bed.external_id}/patient_privacy/",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            # unlock a already unlocked bed
            response = self.client.delete(
                f"/api/v1/consultationbed/{consultation_bed.external_id}/patient_privacy/",
            )
            self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
            self.assertEqual(response.json()["message"], "Asset not locked")
            consultation_bed.delete()
            self.user.delete()

    def test_patient_privacy_toggle_failure(self):
        # lock with existing user login
        consultation_bed = self.create_consultation_bed(
            consultation=self.consultation,
            bed=self.bed,
            start_date=make_aware(datetime.datetime.now()),
            end_date=make_aware(datetime.datetime.now()),
            privacy=False,
        )
        response = self.client.post(
            f"/api/v1/consultationbed/{consultation_bed.external_id}/patient_privacy/",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # locking an already locked should return locking user's details
        response = self.client.post(
            f"/api/v1/consultationbed/{consultation_bed.external_id}/patient_privacy/",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.json()["locked_by"], "test user")

        self.user = self.create_user(
            username="Second test user",
            user_type=User.TYPE_VALUE_MAP["Doctor"],
            district=self.district,
            home_facility=self.facility,
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            f"/api/v1/consultationbed/{consultation_bed.external_id}/patient_privacy/",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.json()["message"], "Asset already locked")
        consultation_bed.delete()

        non_allowed_user_types = [
            "Transportation",
            "Pharmacist",
            "Volunteer",
            "StaffReadOnly",
            # "Reserved",
            # "DistrictLabAdmin",
            "DistrictReadOnlyAdmin",
            # "StateLabAdmin",
            "StateReadOnlyAdmin",
            # "Doctor",
            "Staff",
        ]
        for user_type in non_allowed_user_types:
            facility2 = self.create_facility(
                district=self.district, local_body=self.local_body, user=self.user
            )
            self.user = self.create_user(
                username=f"{user_type} test user",
                user_type=User.TYPE_VALUE_MAP[user_type],
                district=self.district,
                home_facility=facility2,
            )

            consultation_bed = self.create_consultation_bed(
                consultation=self.consultation,
                bed=self.bed,
                start_date=make_aware(datetime.datetime.now()),
                end_date=make_aware(datetime.datetime.now()),
                privacy=True,
            )

            self.client.force_authenticate(user=self.user)
            response = self.client.post(
                f"/api/v1/consultationbed/{consultation_bed.external_id}/patient_privacy/",
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            consultation_bed.delete()
            self.user.delete()
