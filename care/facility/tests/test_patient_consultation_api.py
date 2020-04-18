from rest_framework import status

from care.utils.tests.test_base import TestBase


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
            "bed_number": obj.bed_number,
        }

    def get_detail_representation(self, obj=None) -> dict:
        list_repr = self.get_list_representation(obj)
        detail_repr = list_repr.copy()
        detail_repr.update({})  # no changes in list repr and detail repr, if there are only those may be updated here.
        return detail_repr

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

    def test_detail_api(self):
        consultation = self.create_consultation()
        response = self.client.get(self.get_url(consultation.id))
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.json(), self.get_detail_representation(consultation))
