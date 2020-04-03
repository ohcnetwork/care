from typing import Any

from rest_framework import status

from care.facility.models import Disease, PatientRegistration
from care.utils.tests.test_base import TestBase


class TestPatient(TestBase):
    """Test patient APIs"""

    @classmethod
    def setUpClass(cls):
        """
        Runs once per class
            - Initialize the attributes useful for class methods
        """
        super(TestPatient, cls).setUpClass()
        cls.patient_data = {
            "name": "Foo",
            "age": 32,
            "gender": 2,
            "phone_number": "8888888888",
            "address": "Global citizen",
            "contact_with_confirmed_carrier": True,
            "contact_with_suspected_carrier": True,
            "estimated_contact_date": None,
            "past_travel": False,
            "countries_travelled": None,
            "present_health": "Fine",
            "has_SARI": False,
            "is_active": True,
            "state": None,
            "district": None,
            "local_body": None,
            "facility": None,
            "state_object": None,
            "local_body_object": None,
            "district_object": None,
        }

        cls.patient = PatientRegistration.objects.create(name="Bar", age=31, gender=2, phone_number="7776665554",)
        cls.patient_data["id"] = cls.patient.id

    def get_base_url(self):
        return "/api/v1/patient"

    def get_list_representation(self, patient=None):

        if isinstance(patient, dict):
            medical_history = patient.pop("medical_history", default="[]")
            patient = PatientRegistration(**patient)
            patient.medical_history.set(medical_history)

        return {
            "id": patient.id,
            "name": patient.name,
            "age": patient.age,
            "gender": patient.gender,
            "phone_number": patient.phone_number,
            "address": patient.address,
            "contact_with_confirmed_carrier": patient.contact_with_confirmed_carrier,
            "contact_with_suspected_carrier": patient.contact_with_suspected_carrier,
            "estimated_contact_date": patient.estimated_contact_date,
            "past_travel": patient.past_travel,
            "countries_travelled": patient.countries_travelled,
            "present_health": patient.present_health,
            "has_SARI": patient.has_SARI,
            "is_active": patient.is_active,
            "state": patient.state,
            "district": patient.district,
            "local_body": patient.local_body,
            "facility": patient.facility,
            "state_object": None,
            "local_body_object": None,
            "district_object": None,
        }

    def get_detail_representation(self, patient: Any):
        if isinstance(patient, dict):
            medical_history = patient.pop("medical_history")
            patient = PatientRegistration(**patient)
            patient.medical_history.set(medical_history)

        return {
            "id": patient.id,
            "name": patient.name,
            "age": patient.age,
            "gender": patient.gender,
            "phone_number": patient.phone_number,
            "address": patient.address,
            "contact_with_suspected_carrier": patient.contact_with_suspected_carrier,
            "contact_with_confirmed_carrier": patient.contact_with_confirmed_carrier,
            "estimated_contact_date": patient.estimated_contact_date,
            "medical_history": [],
            "tele_consultation_history": [],
            "is_active": True,
            "state": patient.state,
            "district": patient.district,
            "local_body": patient.local_body,
            "past_travel": patient.past_travel,
            "present_health": patient.present_health,
            "has_SARI": patient.has_SARI,
            "facility": patient.facility,
            "countries_travelled": patient.countries_travelled,
            "last_consultation": None,
            "state_object": None,
            "local_body_object": None,
            "district_object": None,
            "facility_object": None,
        }

    def test_login_required(self):
        """Test permission error is raised for unauthorised access"""
        # logout the user logged in during setUp function
        self.client.logout()
        response = self.client.post(self.get_url(), {},)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patient_creation(self):
        """
        For new patient can be creation, test
            - status code is 201
            - patient data is returned from response
            - patient is created on the backend
        """
        patient_data = self.patient_data
        user = self.user
        response = self.client.post(self.get_url(), patient_data, format="json")

        # breakpoint()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response.data.pop("id")
        self.assertDictEqual(response.data, self.get_detail_representation(patient_data))

        patient = PatientRegistration.objects.get(
            name=patient_data["name"],
            age=patient_data["age"],
            gender=patient_data["gender"],
            phone_number=patient_data["phone_number"],
            contact_with_suspected_carrier=patient_data["contact_with_suspected_carrier"],
            contact_with_confirmed_carrier=patient_data["contact_with_confirmed_carrier"],
            created_by=user,
            is_active=True,
        )
        self.assertIsNotNone(Disease.objects.get(patient=patient, **patient_data["medical_history"][0]))

    def test_users_cant_retrieve_others_patients(self):
        """Test users can't retrieve patients not created by them"""
        response = self.client.get(self.get_url(self.patient.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patient_retrieval(self):
        """
        Test users can retrieve patients created by them
            - test status code
            - test response data
        """
        patient = self.patient
        patient.created_by = self.user
        patient.save()
        response = self.client.get(self.get_url(self.patient.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictEqual(response.data, self.get_detail_representation(patient))

    def test_patient_update(self):
        """
        Test user can update their patient details
            - test status code
            - test response data
            - test data from database
        """
        patient = self.patient
        patient.created_by = self.user
        patient.save()

        new_phone_number = "9999997775"
        response = self.client.put(self.get_url(patient.id), self.get_detail_representation(patient), format="json",)
        # breakpoint()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictEqual(response.data, self.get_detail_representation(self.patient_data))
        patient.refresh_from_db()
        self.assertEqual(patient.phone_number, new_phone_number)

    def test_user_can_delete_patient(self):
        """
        Test users can delete patient
            - test permission error
        """
        patient = self.patient
        patient.created_by = self.user
        patient.save()
        response = self.client.delete(self.get_url(patient.id))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser_can_delete_patient(self):
        """
        Test superuser can delete patient
            - test status code
            - test data from database
        """
        patient = self.patient
        user = self.user
        user.is_superuser = True
        user.save()
        patient.created_by = user

        patient.save()
        response = self.client.delete(self.get_url(patient.id))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        with self.assertRaises(PatientRegistration.DoesNotExist):
            PatientRegistration.objects.get(id=patient.id)

    def test_patient_list_is_accessible_by_url_location(self):
        """Test user can retreive their patient list by the url"""
        patient = self.patient

        patient.created_by = self.user
        patient.save()
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_patient_list_retrieval(self):
        """Test user can retreive their patient list"""
        patient = self.patient

        patient.created_by = self.user
        patient.save()
        response = self.client.get(self.get_url())
        self.assertDictEqual(
            response.data,
            {"count": 1, "next": None, "previous": None, "results": [self.get_list_representation(patient)],},
        )

    def test_superuser_access(self):
        """
        Test superuser can retrieve patient details
            - test status code
            - test response data
        """
        patient = self.patient
        user = self.user
        user.is_superuser = True
        user.save()
        response = self.client.get(self.get_url(entry_id=patient.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictEqual(response.data, self.get_detail_representation(patient))
