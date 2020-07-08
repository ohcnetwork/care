import datetime

from django.utils.timezone import make_aware
from freezegun import freeze_time
from rest_framework import status

from care.facility.api.serializers.patient_sample import PatientSampleSerializer
from care.facility.models import PatientSample
from care.utils.tests.test_base import TestBase
from config.tests.helper import mock_equal


class TestPatientSampleApi(TestBase):
    def get_base_url(self, **kwargs):
        patient = kwargs.get("patient", self.patient)
        return f"/api/v1/patient/{str(patient.external_id)}/test_sample"

    def get_list_representation(self, obj: PatientSample) -> dict:
        return {
            "id": mock_equal,
            "patient_name": obj.patient.name,
            "patient_has_sari": obj.patient.has_SARI,
            "patient_has_confirmed_contact": obj.patient.contact_with_confirmed_carrier,
            "patient_has_suspected_contact": obj.patient.contact_with_suspected_carrier,
            "patient_travel_history": obj.patient.countries_travelled,
            "facility": str(obj.consultation.facility.external_id),
            "facility_object": self.get_facility_representation(obj.consultation.facility),
            "sample_type": obj.get_sample_type_display(),
            "status": obj.get_status_display(),
            "result": obj.get_result_display(),
            "patient": str(obj.patient.external_id),
            "consultation": str(obj.consultation.external_id),
            "date_of_sample": obj.date_of_sample,
            "date_of_result": obj.date_of_result,
            "sample_type_other": obj.sample_type_other,
            "has_sari": obj.has_sari,
            "has_ari": obj.has_ari,
            "doctor_name": obj.doctor_name,
            "diagnosis": obj.diagnosis,
            "diff_diagnosis": obj.diff_diagnosis,
            "etiology_identified": obj.etiology_identified,
            "is_atypical_presentation": obj.is_atypical_presentation,
            "atypical_presentation": obj.atypical_presentation,
            "is_unusual_course": obj.is_unusual_course,
            "fast_track": obj.fast_track,
        }

    def get_detail_representation(self, obj=None) -> dict:
        list_repr = self.get_list_representation(obj)
        detail_repr = list_repr.copy()
        return detail_repr

    def get_sample_data(self, **kwargs):
        patient = kwargs.get("patient", self.patient)
        consultation = kwargs.get("consultation", self.consultation)

        return {
            "patient": str(patient.external_id),
            "consultation": str(consultation.external_id),
            "sample_type": "BA/ETA",
            "testing_facility": str(patient.facility.external_id),
        }

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.consultation = cls.create_consultation(cls.patient, cls.facility)

    def setUp(self) -> None:
        self.client.force_authenticate(self.user)

    def create_sample(self, **kwargs):
        sample_data = self.get_sample_data(**kwargs)
        serializer = PatientSampleSerializer(data=sample_data)
        serializer.is_valid(raise_exception=True)
        return serializer.create(serializer.validated_data)

    def test_create_sample_api(self):
        sample_data = self.get_sample_data()
        response = self.client.post(path=self.get_url(), data=sample_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        sample = self.patient.patientsample_set.last()
        self.assertEqual(sample.result, PatientSample.SAMPLE_TEST_RESULT_MAP["AWAITING"])
        self.assertIsNone(sample.date_of_sample)
        self.assertIsNone(sample.date_of_result)

    def test_sample_flow(self):
        self.client.force_authenticate(self.super_user)

        with freeze_time("2020-04-01"):
            sample = self.create_sample()
            response = self.client.patch(self.get_url(str(sample.external_id)), {"status": "APPROVED"}, format="json")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            sample.refresh_from_db()
            self.assertEquals(sample.status, PatientSample.SAMPLE_TEST_FLOW_MAP["APPROVED"])
            self.assertEquals(sample.result, PatientSample.SAMPLE_TEST_RESULT_MAP["AWAITING"])
            self.assertIsNone(sample.date_of_sample)
            self.assertIsNone(sample.date_of_result)

        with freeze_time("2020-04-02"):
            response = self.client.patch(
                self.get_url(str(sample.external_id)), {"status": "SENT_TO_COLLECTON_CENTRE"}, format="json"
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            sample.refresh_from_db()
            self.assertEquals(sample.status, PatientSample.SAMPLE_TEST_FLOW_MAP["SENT_TO_COLLECTON_CENTRE"])
            self.assertEquals(sample.result, PatientSample.SAMPLE_TEST_RESULT_MAP["AWAITING"])
            self.assertEquals(sample.date_of_sample.date(), make_aware(datetime.datetime(2020, 4, 2)).date())
            self.assertIsNone(sample.date_of_result)

        with freeze_time("2020-04-03"):
            response = self.client.patch(
                self.get_url(str(sample.external_id)), {"status": "RECEIVED_AND_FORWARED"}, format="json"
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            sample.refresh_from_db()
            self.assertEquals(sample.status, PatientSample.SAMPLE_TEST_FLOW_MAP["RECEIVED_AND_FORWARED"])
            self.assertEquals(sample.result, PatientSample.SAMPLE_TEST_RESULT_MAP["AWAITING"])
            self.assertEquals(sample.date_of_sample.date(), make_aware(datetime.datetime(2020, 4, 2)).date())
            self.assertIsNone(sample.date_of_result)

        with freeze_time("2020-04-04"):
            response = self.client.patch(
                self.get_url(str(sample.external_id)), {"status": "RECEIVED_AT_LAB"}, format="json"
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            sample.refresh_from_db()
            self.assertEquals(sample.status, PatientSample.SAMPLE_TEST_FLOW_MAP["RECEIVED_AT_LAB"])
            self.assertEquals(sample.result, PatientSample.SAMPLE_TEST_RESULT_MAP["AWAITING"])
            self.assertEquals(sample.date_of_sample.date(), make_aware(datetime.datetime(2020, 4, 2)).date())
            self.assertIsNone(sample.date_of_result)

        with freeze_time("2020-04-05"):
            response = self.client.patch(self.get_url(str(sample.external_id)), {"result": "NEGATIVE"}, format="json")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            sample.refresh_from_db()
            self.assertEquals(sample.status, PatientSample.SAMPLE_TEST_FLOW_MAP["COMPLETED"])
            self.assertEquals(sample.result, PatientSample.SAMPLE_TEST_RESULT_MAP["NEGATIVE"])
            self.assertEquals(sample.date_of_sample.date(), make_aware(datetime.datetime(2020, 4, 2)).date())
            self.assertEquals(sample.date_of_result.date(), make_aware(datetime.datetime(2020, 4, 5)).date())
