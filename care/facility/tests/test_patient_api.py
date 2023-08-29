from datetime import datetime
from enum import Enum

from django.utils.timezone import make_aware
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from care.facility.models import User
from care.facility.tests.mixins import TestClassMixin
from care.utils.tests.test_base import TestBase


class ExpectedPatientNoteKeys(Enum):
    ID = "id"
    NOTE = "note"
    FACILITY = "facility"
    CREATED_BY_OBJECT = "created_by_object"
    CREATED_DATE = "created_date"
    MODIFIED_DATE = "modified_date"
    EDITS = "edits"
    USER_TYPE = "user_type"


class ExpectedFacilityKeys(Enum):
    ID = "id"
    NAME = "name"
    LOCAL_BODY = "local_body"
    DISTRICT = "district"
    STATE = "state"
    WARD_OBJECT = "ward_object"
    LOCAL_BODY_OBJECT = "local_body_object"
    DISTRICT_OBJECT = "district_object"
    STATE_OBJECT = "state_object"
    FACILITY_TYPE = "facility_type"
    READ_COVER_IMAGE_URL = "read_cover_image_url"
    FEATURES = "features"
    PATIENT_COUNT = "patient_count"
    BED_COUNT = "bed_count"


class ExpectedWardObjectKeys(Enum):
    ID = "id"
    NAME = "name"
    NUMBER = "number"
    LOCAL_BODY = "local_body"


class ExpectedLocalBodyObjectKeys(Enum):
    ID = "id"
    NAME = "name"
    BODY_TYPE = "body_type"
    LOCALBODY_CODE = "localbody_code"
    DISTRICT = "district"


class ExpectedDistrictObjectKeys(Enum):
    ID = "id"
    NAME = "name"
    STATE = "state"


class ExpectedStateObjectKeys(Enum):
    ID = "id"
    NAME = "name"


class ExpectedFacilityTypeKeys(Enum):
    ID = "id"
    NAME = "name"


class ExpectedCreatedByObjectKeys(Enum):
    ID = "id"
    FIRST_NAME = "first_name"
    USERNAME = "username"
    EMAIL = "email"
    LAST_NAME = "last_name"
    USER_TYPE = "user_type"
    LAST_LOGIN = "last_login"


class PatientNotesTestCase(TestBase, TestClassMixin, APITestCase):
    asset_id = None

    def setUp(self):
        self.factory = APIRequestFactory()
        state = self.create_state()
        district = self.create_district(state=state)

        # Create users and facility
        self.user = self.create_user(
            district=district,
            username="test user",
            user_type=User.TYPE_VALUE_MAP["Doctor"],
        )
        facility = self.create_facility(district=district)
        self.user.home_facility = facility
        self.user.save()

        # Create another user from different facility
        self.user2 = self.create_user(
            district=district,
            username="test user 2",
            user_type=User.TYPE_VALUE_MAP["Doctor"],
        )
        facility2 = self.create_facility(district=district)
        self.user2.home_facility = facility2
        self.user2.save()

        self.patient = self.create_patient(district=district.id, facility=facility)

        self.create_patient_note(
            patient=self.patient, facility=facility, created_by=self.user
        )

        self.create_patient_note(
            patient=self.patient, facility=facility, created_by=self.user2
        )

        refresh_token = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh_token.access_token}"
        )

    def test_patient_notes(self):
        patientId = self.patient.external_id
        response = self.client.get(f"/api/v1/patient/{patientId}/notes/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.json()["results"], list)

        # Test user_type field if user is not from same facility as patient
        data2 = response.json()["results"][0]

        user_type_content2 = data2["user_type"]
        self.assertEqual(user_type_content2, "RemoteSpecialist")

        # Ensure only necessary data is being sent and no extra data
        data = response.json()["results"][1]

        self.assertCountEqual(
            data.keys(), [item.value for item in ExpectedPatientNoteKeys]
        )

        user_type_content = data["user_type"]

        self.assertEqual(user_type_content, "Doctor")

        facility_content = data["facility"]

        if facility_content is not None:
            self.assertCountEqual(
                facility_content.keys(), [item.value for item in ExpectedFacilityKeys]
            )

        ward_object_content = facility_content["ward_object"]

        if ward_object_content is not None:
            self.assertCountEqual(
                ward_object_content.keys(),
                [item.value for item in ExpectedWardObjectKeys],
            )

        local_body_object_content = facility_content["local_body_object"]

        if local_body_object_content is not None:
            self.assertCountEqual(
                local_body_object_content.keys(),
                [item.value for item in ExpectedLocalBodyObjectKeys],
            )

        district_object_content = facility_content["district_object"]

        if district_object_content is not None:
            self.assertCountEqual(
                district_object_content.keys(),
                [item.value for item in ExpectedDistrictObjectKeys],
            )

        state_object_content = facility_content["state_object"]

        if state_object_content is not None:
            self.assertCountEqual(
                state_object_content.keys(),
                [item.value for item in ExpectedStateObjectKeys],
            )

        facility_type_content = facility_content["facility_type"]

        if facility_type_content is not None:
            self.assertCountEqual(
                facility_type_content.keys(),
                [item.value for item in ExpectedFacilityTypeKeys],
            )

        created_by_object_content = data["created_by_object"]

        if created_by_object_content is not None:
            self.assertCountEqual(
                created_by_object_content.keys(),
                [item.value for item in ExpectedCreatedByObjectKeys],
            )

    def test_patient_note_edit(self):
        patientId = self.patient.external_id
        response = self.client.get(f"/api/v1/patient/{patientId}/notes/")

        data = response.json()["results"][0]
        self.assertEqual(len(data["edits"]), 1)

        note_id = data["id"]
        note_content = data["note"]
        new_note_content = note_content + " edited"

        response = self.client.put(
            f"/api/v1/patient/{patientId}/notes/{note_id}/", {"note": new_note_content}
        )
        updated_data = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(updated_data["note"], new_note_content)
        self.assertEqual(len(updated_data["edits"]), 2)
        self.assertEqual(updated_data["edits"][0]["note"], new_note_content)
        self.assertEqual(updated_data["edits"][1]["note"], note_content)


class PatientFilterTestCase(TestBase, TestClassMixin, APITestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        state = self.create_state()
        district = self.create_district(state=state)

        self.user = self.create_super_user(district=district, username="test user")
        facility = self.create_facility(district=district, user=self.user)
        self.user.home_facility = facility
        self.user.save()

        self.patient = self.create_patient(district=district.id, created_by=self.user)
        self.consultation = self.create_consultation(
            patient_no="IP5678",
            patient=self.patient,
            facility=facility,
            created_by=self.user,
            suggestion="A",
            admission_date=make_aware(datetime(2020, 4, 1, 15, 30, 00)),
        )
        self.patient.last_consultation = self.consultation
        self.patient.save()
        refresh_token = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh_token.access_token}"
        )

    def test_filter_by_patient_no(self):
        response = self.client.get("/api/v1/patient/?patient_no=IP5678")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(self.patient.external_id)
        )
