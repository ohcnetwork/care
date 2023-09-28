from enum import Enum

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from care.utils.tests.test_utils import TestUtils


class ExpectedShiftListKeys(Enum):
    id = "id"
    patient = "patient"
    patient_object = "patient_object"
    status = "status"
    origin_facility_object = "origin_facility_object"
    shifting_approving_facility_object = "shifting_approving_facility_object"
    assigned_facility = "assigned_facility"
    assigned_facility_external = "assigned_facility_external"
    assigned_facility_object = "assigned_facility_object"
    external_id = "external_id"
    created_date = "created_date"
    modified_date = "modified_date"
    emergency = "emergency"


class PatientObjectKeys(Enum):
    id = "id"
    name = "name"
    allow_transfer = "allow_transfer"
    age = "age"
    phone_number = "phone_number"
    address = "address"
    disease_status = "disease_status"
    facility = "facility"
    facility_object = "facility_object"
    state_object = "state_object"


class FacilityKeys(Enum):
    id = "id"
    name = "name"


class StateKeys(Enum):
    id = "id"
    name = "name"


class ExpectedShiftRetrieveKeys(Enum):
    ID = "id"
    PATIENT = "patient"
    PATIENT_OBJECT = "patient_object"
    STATUS = "status"
    BREATHLESSNESS_LEVEL = "breathlessness_level"
    ORIGIN_FACILITY = "origin_facility"
    ORIGIN_FACILITY_OBJECT = "origin_facility_object"
    SHIFTING_APPROVING_FACILITY = "shifting_approving_facility"
    SHIFTING_APPROVING_FACILITY_OBJECT = "shifting_approving_facility_object"
    ASSIGNED_FACILITY = "assigned_facility"
    ASSIGNED_FACILITY_EXTERNAL = "assigned_facility_external"
    ASSIGNED_FACILITY_OBJECT = "assigned_facility_object"
    ASSIGNED_FACILITY_TYPE = "assigned_facility_type"
    PREFERRED_VEHICLE_CHOICE = "preferred_vehicle_choice"
    ASSIGNED_TO_OBJECT = "assigned_to_object"
    CREATED_BY_OBJECT = "created_by_object"
    LAST_EDITED_BY_OBJECT = "last_edited_by_object"
    AMBULANCE_DRIVER_NAME = "ambulance_driver_name"
    AMBULANCE_NUMBER = "ambulance_number"
    EXTERNAL_ID = "external_id"
    CREATED_DATE = "created_date"
    MODIFIED_DATE = "modified_date"
    EMERGENCY = "emergency"
    IS_UP_SHIFT = "is_up_shift"
    REASON = "reason"
    VEHICLE_PREFERENCE = "vehicle_preference"
    COMMENTS = "comments"
    REFERING_FACILITY_CONTACT_NAME = "refering_facility_contact_name"
    REFERING_FACILITY_CONTACT_NUMBER = "refering_facility_contact_number"
    IS_KASP = "is_kasp"
    IS_ASSIGNED_TO_USER = "is_assigned_to_user"
    AMBULANCE_PHONE_NUMBER = "ambulance_phone_number"
    ASSIGNED_TO = "assigned_to"
    CREATED_BY = "created_by"
    LAST_EDITED_BY = "last_edited_by"


class ExpectedShiftCommentListCreatedByKeys(Enum):
    ID = "id"
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"


class ExpectedShiftCommentListKeys(Enum):
    ID = "id"
    COMMENT = "comment"
    MODIFIED_DATE = "modified_date"
    CREATED_BY_OBJECT = "created_by_object"


class ExpectedShiftCommentRetrieveCreatedByKeys(Enum):
    ID = "id"
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    USERNAME = "username"
    EMAIL = "email"
    USER_TYPE = "user_type"
    LAST_LOGIN = "last_login"


class ExpectedShiftCommentRetrieveKeys(Enum):
    ID = "id"
    COMMENT = "comment"
    CREATED_BY_OBJECT = "created_by_object"
    EXTERNAL_ID = "external_id"
    CREATED_DATE = "created_date"
    MODIFIED_DATE = "modified_date"
    CREATED_BY = "created_by"


class ShiftingViewSetTestCase(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.user = cls.create_user(
            username="test_user", district=cls.district, local_body=cls.local_body
        )
        cls.facility = cls.create_facility(
            user=cls.user, district=cls.district, local_body=cls.local_body
        )
        cls.patient = cls.create_patient(cls.district, cls.facility)
        cls.patient_shift = cls.create_patient_shift(
            facility=cls.facility, user=cls.user, patient=cls.patient
        )

    def setUp(self) -> None:
        refresh_token = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh_token.access_token}"
        )

    def test_list_shift(self):
        response = self.client.get("/api/v1/shift/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.json()["results"], list)

        expected_keys = [key.value for key in ExpectedShiftListKeys]
        data = response.json()["results"][0]
        self.assertCountEqual(data.keys(), expected_keys)

    def test_retrieve_shift(self):
        response = self.client.get(f"/api/v1/shift/{self.patient_shift.external_id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_keys = [key.value for key in ExpectedShiftRetrieveKeys]
        data = response.json()
        self.assertCountEqual(data.keys(), expected_keys)


class ShifitngRequestCommentViewSetTestCase(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.user = cls.create_user(
            username="test_user", district=cls.district, local_body=cls.local_body
        )
        cls.facility = cls.create_facility(
            user=cls.user, district=cls.district, local_body=cls.local_body
        )
        cls.patient = cls.create_patient(cls.district, cls.facility)
        cls.patient_shift = cls.create_patient_shift(
            facility=cls.facility, user=cls.user, patient=cls.patient
        )
        cls.patient_shift_comment = cls.create_patient_shift_comment(
            resource=cls.patient_shift
        )

    def setUp(self) -> None:
        refresh_token = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh_token.access_token}"
        )

    def test_list_shift_request_comment(self):
        response = self.client.get(
            f"/api/v1/shift/{self.patient_shift.external_id}/comment/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.json()["results"], list)

        expected_keys = [key.value for key in ExpectedShiftCommentListKeys]
        data = response.json()["results"][0]
        self.assertCountEqual(data.keys(), expected_keys)

        expected_created_by_keys = [
            key.value for key in ExpectedShiftCommentListCreatedByKeys
        ]
        data = response.json()["results"][0]["created_by_object"]
        if data:
            self.assertCountEqual(data.keys(), expected_created_by_keys)

    def test_retrieve_shift_request_comment(self):
        response = self.client.get(
            f"/api/v1/shift/{self.patient_shift.external_id}/comment/{self.patient_shift_comment.external_id}/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_keys = [key.value for key in ExpectedShiftCommentRetrieveKeys]
        data = response.json()
        self.assertCountEqual(data.keys(), expected_keys)

        expected_created_by_keys = [
            key.value for key in ExpectedShiftCommentRetrieveCreatedByKeys
        ]
        data = response.json()["created_by_object"]
        if data:
            self.assertCountEqual(data.keys(), expected_created_by_keys)
