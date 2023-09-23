from enum import Enum

from django.utils.timezone import now
from rest_framework import status
from rest_framework.test import APITestCase

from care.utils.tests.test_utils import TestUtils


class ExpectedPatientNoteKeys(Enum):
    NOTE = "note"
    FACILITY = "facility"
    CREATED_BY_OBJECT = "created_by_object"
    CREATED_DATE = "created_date"
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


class PatientNotesTestCase(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.user = cls.create_user(
            "doctor1", cls.district, home_facility=cls.facility, user_type=15
        )
        cls.asset_location = cls.create_asset_location(cls.facility)
        cls.asset = cls.create_asset(cls.asset_location)
        cls.state_admin = cls.create_user(
            "state-admin", cls.district, home_facility=cls.facility, user_type=40
        )

        cls.facility2 = cls.create_facility(
            cls.super_user, cls.district, cls.local_body
        )
        cls.user2 = cls.create_user(
            "doctor2", cls.district, home_facility=cls.facility2, user_type=15
        )
        cls.patient = cls.create_patient(cls.district, cls.facility)

    def setUp(self):
        super().setUp()
        self.create_patient_note(
            patient=self.patient, facility=self.facility, created_by=self.user
        )
        self.create_patient_note(
            patient=self.patient, facility=self.facility, created_by=self.user2
        )

    def create_patient_note(
        self, patient=None, note="Patient is doing find", created_by=None, **kwargs
    ):
        data = {
            "facility": patient.facility or self.facility,
            "note": note,
        }
        data.update(kwargs)
        self.client.force_authenticate(user=created_by)
        self.client.post(f"/api/v1/patient/{patient.external_id}/notes/", data=data)

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


class PatientFilterTestCase(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.user = cls.create_user(
            "doctor1", cls.district, home_facility=cls.facility, user_type=15
        )
        cls.patient = cls.create_patient(cls.district, cls.facility)
        cls.consultation = cls.create_consultation(
            patient_no="IP5678",
            patient=cls.patient,
            facility=cls.facility,
            created_by=cls.user,
            suggestion="A",
            admission_date=now(),
        )
        cls.patient.last_consultation = cls.consultation
        cls.patient.save()

    def test_filter_by_patient_no(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/patient/?patient_no=IP5678")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(self.patient.external_id)
        )
