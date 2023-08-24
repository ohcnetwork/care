import random
from enum import Enum

from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from care.facility.models import MedibaseMedicine
from care.facility.tests.mixins import TestClassMixin
from care.utils.tests.test_base import TestBase


class ExpectedPrescriptionKeys(Enum):
    ID = "id"
    MEDICINE_OBJECT = "medicine_object"
    MEDICINE_OLD = "medicine_old"
    CREATED_DATE = "created_date"


class ExpectedMedicineObjectListKeys(Enum):
    ID = "id"
    NAME = "name"
    CREATED_DATE = "created_date"
    MODIFIED_DATE = "modified_date"


class ExpectedAdministeredByKeys(Enum):
    ID = "id"
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"


class ExpectedMedicineAdministrationListKeys(Enum):
    ID = "id"
    PRESCRIPTION = "prescription"
    CREATED_DATE = "created_date"
    ADMINISTERED_BY = "administered_by"
    NOTES = "notes"
    MODIFIED_DATE = "modified_date"


class ExpectedMedicineListKeys(Enum):
    ID = "id"
    NAME = "name"
    CREATED_DATE = "created_date"
    MODIFIED_DATE = "modified_date"


class ExpectedPrescriptionListKeys(Enum):
    ID = "id"
    LAST_ADMINISTERED_ON = "last_administered_on"
    MEDICINE_OBJECT = "medicine_object"
    MODIFIED_DATE = "modified_date"
    PRESCRIPTION_TYPE = "prescription_type"
    MEDICINE_OLD = "medicine_old"
    ROUTE = "route"
    DOSAGE = "dosage"
    IS_PRN = "is_prn"
    FREQUENCY = "frequency"
    DAYS = "days"
    INDICATOR = "indicator"
    MAX_DOSAGE = "max_dosage"
    MIN_HOURS_BETWEEN_DOSES = "min_hours_between_doses"
    NOTES = "notes"
    DISCONTINUED = "discontinued"
    DISCONTINUED_REASON = "discontinued_reason"


class ExpectedPrescribedByRetrieveKeys(Enum):
    ID = "id"
    FIRST_NAME = "first_name"
    USERNAME = "username"
    EMAIL = "email"
    LAST_NAME = "last_name"
    USER_TYPE = "user_type"
    LAST_LOGIN = "last_login"


# class ExpectedMedicineRetrieveKeys(Enum):
#     ID = "id"
#     EXTERNAL_ID = "external_id"
#     CREATED_DATE = "created_date"
#     MODIFIED_DATE = "modified_date"
#     NAME = "name"
#     TYPE = "type"
#     GENERIC = "generic"
#     COMPANY = "company"
#     CONTENTS = "contents"
#     CIMS_CLASS = "cims_class"
#     ATC_CLASSIFICATION = "atc_classification"

# class ExpectedPrescriptionRetrieveKeys(Enum):
#     ID = "id"
#     PRESCRIBED_BY = "prescribed_by"
#     LAST_ADMINISTERED_ON = "last_administered_on"
#     MEDICINE_OBJECT = "medicine_object"
#     EXTERNAL_ID = "external_id"
#     CREATED_DATE = "created_date"
#     MODIFIED_DATE = "modified_date"
#     PRESCRIPTION_TYPE = "prescription_type"
#     MEDICINE_OLD = "medicine_old"
#     ROUTE = "route"
#     DOSAGE = "dosage"
#     IS_PRN = "is_prn"
#     FREQUENCY = "frequency"
#     DAYS = "days"
#     INDICATOR = "indicator"
#     MAX_DOSAGE = "max_dosage"
#     MIN_HOURS_BETWEEN_DOSES = "min_hours_between_doses"
#     NOTES = "notes"
#     META = "meta"
#     DISCONTINUED = "discontinued"
#     DISCONTINUED_REASON = "discontinued_reason"
#     DISCONTINUED_DATE = "discontinued_date"
#     IS_MIGRATED = "is_migrated"


class ExpectedAdministeredByRetrieveKeys(Enum):
    ID = "id"
    FIRST_NAME = "first_name"
    USERNAME = "username"
    EMAIL = "email"
    LAST_NAME = "last_name"
    USER_TYPE = "user_type"
    LAST_LOGIN = "last_login"


class ExpectedMedicineRetrieveKeys(Enum):
    ID = "id"
    EXTERNAL_ID = "external_id"
    CREATED_DATE = "created_date"
    MODIFIED_DATE = "modified_date"
    NAME = "name"
    TYPE = "type"
    GENERIC = "generic"
    COMPANY = "company"
    CONTENTS = "contents"
    CIMS_CLASS = "cims_class"
    ATC_CLASSIFICATION = "atc_classification"


class ExpectedPrescriptionRetrieveKeys(Enum):
    ID = "id"
    PRESCRIBED_BY = "prescribed_by"
    LAST_ADMINISTERED_ON = "last_administered_on"
    MEDICINE_OBJECT = "medicine_object"
    EXTERNAL_ID = "external_id"
    CREATED_DATE = "created_date"
    MODIFIED_DATE = "modified_date"
    PRESCRIPTION_TYPE = "prescription_type"
    MEDICINE_OLD = "medicine_old"
    ROUTE = "route"
    DOSAGE = "dosage"
    IS_PRN = "is_prn"
    FREQUENCY = "frequency"
    DAYS = "days"
    INDICATOR = "indicator"
    MAX_DOSAGE = "max_dosage"
    MIN_HOURS_BETWEEN_DOSES = "min_hours_between_doses"
    NOTES = "notes"
    META = "meta"
    DISCONTINUED = "discontinued"
    DISCONTINUED_REASON = "discontinued_reason"
    DISCONTINUED_DATE = "discontinued_date"
    IS_MIGRATED = "is_migrated"


class ExpectedAdministeredPrescriptionRetrieveKeys(Enum):
    ID = "id"
    ADMINISTERED_BY = "administered_by"
    PRESCRIPTION = "prescription"
    EXTERNAL_ID = "external_id"
    CREATED_DATE = "created_date"
    MODIFIED_DATE = "modified_date"
    NOTES = "notes"
    ADMINISTERED_DATE = "administered_date"


class ConsultationPrescriptionViewSetTestCase(TestBase, TestClassMixin, APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.factory = APIRequestFactory()

    def setUp(self) -> None:
        refresh_token = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh_token.access_token}"
        )

    def test_list_prescription(self):
        response = self.client.get(
            f"/api/v1/consultation/{self.consultation.external_id}/prescriptions/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.json()["results"], list)

        expected_keys = [key.value for key in ExpectedPrescriptionListKeys]
        data = response.json()["results"][0]
        self.assertCountEqual(data.keys(), expected_keys)

        expected_medicine_objects_keys = [
            key.value for key in ExpectedMedicineObjectListKeys
        ]
        data = response.json()["results"][0]["medicine_object"]
        self.assertCountEqual(data.keys(), expected_medicine_objects_keys)

    def test_retrieve_prescription(self):
        response = self.client.get(
            f"/api/v1/consultation/{self.consultation.external_id}/prescriptions/{self.prescription.external_id}/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_keys = [key.value for key in ExpectedPrescriptionRetrieveKeys]
        data = response.json()
        self.assertCountEqual(data.keys(), expected_keys)

        expected_prescribed_by_keys = [
            key.value for key in ExpectedPrescribedByRetrieveKeys
        ]
        data = response.json()["prescribed_by"]
        self.assertCountEqual(data.keys(), expected_prescribed_by_keys)

    def test_create_prescription(self):
        medicine = random.choice(MedibaseMedicine.objects.all())
        data = {
            "medicine": medicine.external_id,
            "prescription_type": "REGULAR",
            "medicine_old": "Paracetamol",
            "route": "ORAL",
            "dosage": "1-0-1",
            "is_prn": False,
            "frequency": "OD",
            "days": 5,
            "indicator": "Take only when fever is above 100",
            "max_dosage": "2-0-2",
            "min_hours_between_doses": 4,
            "notes": "Take with water",
            "meta": {},
            "prescribed_by": self.user.external_id,
            "discontinued": False,
            "discontinued_reason": "",
            "discontinued_date": None,
            "is_migrated": False,
        }
        response = self.client.post(
            f"/api/v1/consultation/{self.consultation.external_id}/prescriptions/",
            data=data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class MedicineAdministrationViewSetTestCase(TestBase, TestClassMixin, APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.factory = APIRequestFactory()

    def setUp(self) -> None:
        refresh_token = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh_token.access_token}"
        )

    def test_list_medicine_administration(self):
        url = f"/api/v1/consultation/{self.consultation.external_id}/prescription_administration/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.json()["results"], list)

        expected_keys = [key.value for key in ExpectedMedicineAdministrationListKeys]
        data = response.json()["results"][0]
        self.assertCountEqual(data.keys(), expected_keys)

        expected_administered_by_keys = [
            key.value for key in ExpectedAdministeredByKeys
        ]
        data = response.json()["results"][0]["administered_by"]
        self.assertCountEqual(data.keys(), expected_administered_by_keys)

    def test_retrieve_medicine_administration_keys(self):
        url = f"/api/v1/consultation/{self.consultation.external_id}/prescription_administration/{self.medicine_administration.external_id}/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_keys = [
            key.value for key in ExpectedAdministeredPrescriptionRetrieveKeys
        ]
        data = response.json()
        self.assertCountEqual(data.keys(), expected_keys)

        expected_administered_by_keys = [
            key.value for key in ExpectedAdministeredByRetrieveKeys
        ]
        data = response.json()["administered_by"]
        self.assertCountEqual(data.keys(), expected_administered_by_keys)

        expected_prescription_keys = [
            key.value for key in ExpectedPrescriptionRetrieveKeys
        ]
        data = response.json()["prescription"]
        self.assertCountEqual(data.keys(), expected_prescription_keys)
