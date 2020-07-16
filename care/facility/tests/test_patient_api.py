import datetime
from typing import Any

from rest_framework import status

from care.facility.models import DiseaseStatusEnum, PatientContactDetails, PatientRegistration, PatientSearch
from care.utils.tests.test_base import TestBase
from config.tests.helper import mock_equal


class TestPatient(TestBase):
    """Test patient APIs"""

    @classmethod
    def setUpClass(cls):
        """
        Runs once per class
            - Initialize the attributes useful for class methods
        """
        super(TestPatient, cls).setUpClass()

    def get_base_url(self):
        return "/api/v1/patient"

    def get_list_representation(self, patient=None):

        if isinstance(patient, dict):
            medical_history = patient.pop("medical_history", [])
            patient = PatientRegistration(**patient)
            patient.medical_history.set(medical_history)

        facility_id = None
        if getattr(patient.facility, "external_id", None):
            facility_id = str(getattr(patient.facility, "external_id", None))
        return {
            "id": str(str(patient.external_id)),
            "name": patient.name,
            "age": patient.age,
            "date_of_birth": mock_equal,
            "gender": patient.gender,
            "is_medical_worker": patient.is_medical_worker,
            "is_antenatal": patient.is_antenatal,
            "phone_number": patient.phone_number,
            "address": patient.address,
            "pincode": patient.pincode,
            "nationality": patient.nationality,
            "passport_no": patient.passport_no,
            # "aadhar_no": patient.aadhar_no,
            "contact_with_confirmed_carrier": patient.contact_with_confirmed_carrier,
            "contact_with_suspected_carrier": patient.contact_with_suspected_carrier,
            "estimated_contact_date": patient.estimated_contact_date,
            "past_travel": patient.past_travel,
            "countries_travelled": patient.countries_travelled,
            "present_health": patient.present_health,
            "has_SARI": patient.has_SARI,
            "is_active": patient.is_active,
            "facility": facility_id,
            "facility_object": self.get_facility_representation(patient.facility),
            "blood_group": patient.blood_group,
            "allow_transfer": patient.allow_transfer,
            "date_of_return": patient.date_of_return,
            "disease_status": self._get_disease_state_representation(patient.disease_status),
            "number_of_aged_dependents": patient.number_of_aged_dependents,
            "number_of_chronic_diseased_dependents": patient.number_of_chronic_diseased_dependents,
            "created_date": mock_equal,
            "modified_date": mock_equal,
            "source": patient.get_source_display(),
            "nearest_facility": getattr(patient.nearest_facility, "id", None),
            **self.get_local_body_district_state_representation(patient),
            "date_of_receipt_of_information": patient.date_of_receipt_of_information,
        }

    def _get_medical_history_representation(self, history):
        if isinstance(history, list):
            return history
        else:
            return [{"disease": h.get_disease_display(), "details": h.details} for h in history.all()]

    def _get_disease_state_representation(self, disease_state):
        if isinstance(disease_state, int):
            return DiseaseStatusEnum(disease_state).name
        return disease_state

    def _get_metainfo_representation(self, patient: PatientRegistration):
        if not patient.meta_info:
            return None
        return {
            "occupation": patient.meta_info.get_occupation_display(),
            "head_of_household": patient.meta_info.head_of_household,
        }

    def _get_contact_patients_representation(self, patient: PatientRegistration):
        return [
            {
                "patient_in_contact": contacted_patient.patient_in_contact,
                "patient_in_contact_object": self.get_list_representation(contacted_patient.patient_in_contact),
                "relation_with_patient": contacted_patient.get_relation_with_patient_display(),
                "mode_of_contact": contacted_patient.get_mode_of_contact_display(),
                "date_of_first_contact": contacted_patient.date_of_first_contact,
                "date_of_last_contact": contacted_patient.date_of_last_contact,
                "is_primary": contacted_patient.is_primary,
                "condition_of_contact_is_symptomatic": contacted_patient.condition_of_contact_is_symptomatic,
            }
            for contacted_patient in patient.contacted_patients.all()
        ]

    def get_detail_representation(self, patient: Any):

        if isinstance(patient, dict):
            this_patient = patient.copy()
            medical_history = this_patient.pop("medical_history", [])
            this_patient_data = this_patient.copy()
            district_id = this_patient_data.pop("district")
            state_id = this_patient_data.pop("state")
            this_patient_data.update({"district_id": district_id, "state_id": state_id})
            patient = PatientRegistration(**this_patient_data)

        else:
            medical_history = patient.medical_history

        return {
            "id": mock_equal,
            "name": patient.name,
            "age": patient.age,
            "date_of_birth": mock_equal,
            "nationality": patient.nationality,
            "passport_no": patient.passport_no,
            # "aadhar_no": patient.aadhar_no,
            "is_medical_worker": patient.is_medical_worker,
            "is_antenatal": patient.is_antenatal,
            "blood_group": patient.blood_group,
            "allergies": patient.allergies,
            "allow_transfer": patient.allow_transfer,
            "ongoing_medication": patient.ongoing_medication,
            "date_of_return": patient.date_of_return,
            "disease_status": self._get_disease_state_representation(patient.disease_status),
            "gender": patient.gender,
            "phone_number": patient.phone_number,
            "address": patient.address,
            "pincode": patient.pincode,
            "contact_with_suspected_carrier": patient.contact_with_suspected_carrier,
            "contact_with_confirmed_carrier": patient.contact_with_confirmed_carrier,
            "estimated_contact_date": patient.estimated_contact_date,
            "number_of_aged_dependents": patient.number_of_aged_dependents,
            "number_of_chronic_diseased_dependents": patient.number_of_chronic_diseased_dependents,
            "medical_history": self._get_medical_history_representation(medical_history),
            "tele_consultation_history": [],
            "is_active": True,
            "past_travel": patient.past_travel,
            "present_health": patient.present_health,
            "has_SARI": patient.has_SARI,
            "facility": patient.facility,
            "countries_travelled": patient.countries_travelled,
            "last_consultation": None,
            "facility_object": None,
            "created_date": mock_equal,
            "modified_date": mock_equal,
            "source": patient.get_source_display(),
            **self.get_local_body_district_state_representation(patient),
            "nearest_facility": patient.nearest_facility,
            "nearest_facility_object": self.get_facility_representation(patient.nearest_facility),
            "meta_info": self._get_metainfo_representation(patient),
            "contacted_patients": self._get_contact_patients_representation(patient),
            "date_of_receipt_of_information": mock_equal,
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
        patient_data = self.patient_data.copy()
        patient_data["countries_travelled"] = [
            "country1",
        ]
        unverified_user = self.clone_object(self.user, save=False)
        unverified_user.username = "unverified_user_test_patient_creation"
        unverified_user.verified = False
        unverified_user.save()

        self.client.force_authenticate(unverified_user)
        response = self.client.post(self.get_url(), patient_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)  # only for verified users

        self.client.force_authenticate(self.user)
        response = self.client.post(self.get_url(), patient_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertDictEqual(response.json(), self.get_detail_representation(patient_data))

        patient = PatientRegistration.objects.filter(countries_travelled=patient_data["countries_travelled"]).first()
        self.assertIsNotNone(patient)
        self.assertIsNotNone(patient.medical_history.all().count(), len(patient_data["medical_history"]))

        self.assertIsNotNone(patient.patient_search_id)
        patient_search = PatientSearch.objects.get(pk=patient.patient_search_id)
        self.assertIsNotNone(patient_search)
        self.assertEqual(patient_search.phone_number, patient_data["phone_number"])

    def test_users_cant_retrieve_others_patients(self):
        """Test users can't retrieve patients not created by them"""
        response = self.client.get(self.get_url(str(self.patient.external_id)))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patient_retrieval(self):
        """
        Test users can retrieve patients created by them
            - test status code
            - test response.json()
        """
        patient = self.patient
        patient.created_by = self.user
        patient.save()
        response = self.client.get(self.get_url(str(self.patient.external_id)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictEqual(response.json(), self.get_detail_representation(patient))

    def test_patient_patch(self):
        """
        Test user can update their patient details
            - test status code
            - test response.json()
            - test data from database
        """
        patient = self.clone_object(self.patient)
        patient.created_by = self.user
        patient.save()

        unverified_user = self.clone_object(self.user, save=False)
        unverified_user.username = "unverified_user_test_patient_creation"
        unverified_user.verified = False
        unverified_user.save()

        new_disease_status = DiseaseStatusEnum.NEGATIVE

        self.client.force_authenticate(unverified_user)
        response = self.client.patch(
            self.get_url(str(patient.external_id)), {"disease_status": new_disease_status.value}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)  # only for verified users

        self.client.force_authenticate(self.user)
        response = self.client.patch(
            self.get_url(str(patient.external_id)), {"disease_status": new_disease_status.value}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)  # only for verified users

        patient.refresh_from_db()
        self.assertEqual(patient.disease_status, new_disease_status.value)

    def test_patient_put(self):
        """
        Test user can update their patient details
            - test status code
            - test response.json()
            - test data from database
        """
        patient = self.clone_object(self.patient)
        patient.created_by = self.user
        patient.contacted_patients.add(
            PatientContactDetails(
                **{
                    "patient_in_contact": self.patient,
                    "relation_with_patient": PatientContactDetails.RelationEnum.FAMILY_MEMBER.value,
                    "mode_of_contact": PatientContactDetails.ModeOfContactEnum.CLEANED_USED_ITEMS.value,
                    "date_of_last_contact": datetime.datetime(2020, 4, 1),
                    "is_primary": True,
                    "condition_of_contact_is_symptomatic": False,
                }
            ),
            bulk=False,
        )
        patient.save()
        patient.refresh_from_db()

        new_disease_status = DiseaseStatusEnum.NEGATIVE
        data = self.get_detail_representation(patient)
        data.update(
            {
                "disease_status": new_disease_status.value,
                "contacted_patients": [
                    {
                        "patient_in_contact": str(self.patient.external_id),
                        "relation_with_patient": PatientContactDetails.RelationEnum.FRIEND.name,
                        "mode_of_contact": PatientContactDetails.ModeOfContactEnum.CO_PASSENGER_AEROPLANE.name,
                        "date_of_last_contact": "2020-04-10",
                        "is_primary": True,
                        "condition_of_contact_is_symptomatic": False,
                    }
                ],
            }
        )
        keys_to_pop = [key for key, value in data.items() if value is mock_equal] + [
            "meta_info",
            "nationality",
            "passport_no",
            # "aadhar_no",
        ]
        for key in keys_to_pop:
            data.pop(key)

        response = self.client.put(self.get_url(str(patient.external_id)), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)  # only for verified users

        patient.refresh_from_db()
        self.assertEqual(patient.disease_status, new_disease_status.value)
        self.assertEquals(patient.contacted_patients.count(), 1)

        contacted_patient = patient.contacted_patients.first()
        self.assertEquals(contacted_patient.relation_with_patient, PatientContactDetails.RelationEnum.FRIEND.value)
        self.assertEquals(
            contacted_patient.mode_of_contact, PatientContactDetails.ModeOfContactEnum.CO_PASSENGER_AEROPLANE.value
        )
        self.assertEquals(contacted_patient.date_of_last_contact, datetime.date(2020, 4, 10))

    def test_user_can_delete_patient(self):
        """
        Test users can delete patient
            - test permission error
        """
        user = self.clone_object(self.user, save=False)
        user.username = "username__test_user_can_delete_patient"
        user.save()

        patient = self.clone_object(self.patient)
        patient.created_by = self.user
        patient.save()

        self.client.force_authenticate(user)
        response = self.client.delete(self.get_url(str(patient.external_id)))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.client.force_authenticate(self.user)
        response = self.client.delete(self.get_url(str(patient.external_id)))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

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
        response = self.client.delete(self.get_url(str(patient.external_id)))
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
        patient = self.clone_object(self.patient)
        patient_2 = self.clone_object(self.patient)

        patient.created_by = self.user
        patient.save()

        patient_2.name = "patient 2"
        patient_2.created_by = self.user
        patient_2.facility = self.facility
        patient_2.save()

        response = self.client.get(self.get_url())
        self.assertDictEqual(
            response.json(),
            {"count": 1, "next": None, "previous": None, "results": [self.get_list_representation(patient_2)],},
        )

        response = self.client.get(f"{self.get_url()}?without_facility=true")
        self.assertDictEqual(
            response.json(),
            {"count": 1, "next": None, "previous": None, "results": [self.get_list_representation(patient)],},
        )

    def test_superuser_access(self):
        """
        Test superuser can retrieve patient details
            - test status code
            - test response.json()
        """
        patient = self.patient
        user = self.user
        user.is_superuser = True
        user.save()
        response = self.client.get(self.get_url(entry_id=str(patient.external_id)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictEqual(response.json(), self.get_detail_representation(patient))

    def test_search(self):
        user = self.clone_object(self.user, save=False)
        user.username = f"{user.username}_verified_test_search"
        user.verified = False
        user.save()

        self.client.force_authenticate(user)
        response = self.client.get(f"{self.get_url()}search/?phone_number={self.patient.phone_number}")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.user)
        response = self.client.get(f"{self.get_url()}search/?phone_number={self.patient.phone_number}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(self.super_user)
        response = self.client.get(f"{self.get_url()}search/?phone_number={self.patient.phone_number}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # def test_icmr_sample__should_render(self):
    #     patient = self.clone_object(self.patient, save=False)
    #     patient.created_by = self.user
    #     patient.save()

    #     response = self.client.get(self.get_url(str(patient.external_id), "icmr_sample"))
    #     self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_patient_transfer(self):
        patient = self.clone_object(self.patient)
        patientsearch = PatientSearch.objects.get(id=patient.patient_search_id)

        new_facility_user = self.clone_object(self.user, save=False)
        new_facility_user.username = f"{new_facility_user.username}_test_patient_transfer"
        new_facility_user.save()

        new_facility = self.clone_object(self.facility, save=False)
        new_facility.created_by = new_facility_user
        new_facility.save()

        self.client.force_authenticate(new_facility_user)

        # check for invalid date of birth
        response = self.client.post(
            self.get_url(str(patientsearch.external_id), "transfer"),
            {"facility": str(new_facility.external_id), "date_of_birth": "2020-04-01"},
        )
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

        # check for valid date of birth
        response = self.client.post(
            self.get_url(str(patientsearch.external_id), "transfer"),
            {"facility": str(new_facility.external_id), "date_of_birth": patient.date_of_birth.strftime("%Y-%m-%d")},
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        patient.refresh_from_db()
        self.assertEquals(patient.facility, new_facility)

        # new owner should be able to view the details
        response = self.client.get(self.get_url(str(patient.external_id)))
        self.assertEquals(response.status_code, status.HTTP_200_OK)
