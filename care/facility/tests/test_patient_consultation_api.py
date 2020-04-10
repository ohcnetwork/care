import datetime

from care.facility.models import CATEGORY_CHOICES, SYMPTOM_CHOICES, PatientConsultation
from care.utils.tests.test_base import TestBase
from config.tests.helper import mock_equal


class TestPatientConsultationApi(TestBase):
    def get_base_url(self):
        return "/api/v1/consultation"

    def get_list_representation(self, obj) -> dict:
        return {
            "id": obj.id,
            "patient": obj.patient.id,
            "facility": obj.facility.id,
            "facility_name": obj.facility.name,
            "symptoms": obj.symptoms,
            "other_symptoms": obj.other_symptoms,
            "symptoms_onset_date": obj.symptoms_onset_date,
            "category": obj.get_category_display(),
            "examination_details": obj.examination_details,
            "existing_medication": obj.existing_medication,
            "prescribed_medication": obj.prescribed_medication,
            "suggestion": obj.suggestion,
            "suggestion_text": obj.get_suggestion_display(),
            "referred_to": obj.referred_to,
            "admitted": obj.admitted,
            "admitted_to": obj.admitted_to,
            "admission_date": obj.admission_date,
            "discharge_date": obj.discharge_date,
            "created_date": obj.created_date,
            "modified_date": obj.modified_date,
        }

    def get_detail_representation(self, obj=None) -> dict:
        list_repr = self.get_list_representation(obj)
        detail_repr = list_repr.copy()
        detail_repr.update({})  # no changes in list repr and detail repr, if there are only those may be updated here.
        return detail_repr

    def get_consultation_data(self):
        return {
            "patient": self.patient,
            "facility": self.facility,
            "symptoms": [SYMPTOM_CHOICES[0][0], SYMPTOM_CHOICES[1][0]],
            "other_symptoms": "No other symptoms",
            "symptoms_onset_date": datetime.datetime(2020, 4, 7, 15, 30),
            "category": CATEGORY_CHOICES[0][0],
            "examination_details": "examination_details",
            "existing_medication": "existing_medication",
            "prescribed_medication": "prescribed_medication",
            "suggestion": PatientConsultation.SUGGESTION_CHOICES[0][0],
            "referred_to": None,
            "admitted": False,
            "admitted_to": None,
            "admission_date": None,
            "discharge_date": None,
            "created_date": mock_equal,
            "modified_date": mock_equal,
        }

    def create_consultation(self, patient=None, facility=None, **kwargs) -> PatientConsultation:
        data = self.get_consultation_data()
        kwargs.update({"patient": patient or self.patient, "facility": facility or self.facility})
        data.update(kwargs)
        return PatientConsultation.objects.create(**data)

    def test_list__should_order_in_desc_order(self):
        consultation_1 = self.create_consultation()
        consultation_2 = self.create_consultation()

        response = self.execute_list()
        self.assertEqual(
            response.json(),
            {
                "count": 2,
                "next": None,
                "previous": None,
                "results": [self.get_list_representation(consultation_2), self.get_list_representation(consultation_1)],
            },
        )
