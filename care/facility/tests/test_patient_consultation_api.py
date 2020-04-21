from rest_framework import status

from care.facility.models import FACILITY_TYPES
from care.utils.tests.test_base import TestBase


class TestPatientConsultationApi(TestBase):
    def get_base_url(self):
        return "/api/v1/consultation"

    def get_list_representation(self, obj, facility_obj=None) -> dict:
        referred_to_object = None
        referred_to = obj.referred_to
        if obj.referred_to:
            referred_to_object = {
                "id": facility_obj.id,
                "name": facility_obj.name,
                "local_body": facility_obj.local_body,
                "district": facility_obj.district.id,
                "state": facility_obj.state.id,
                "local_body_object": facility_obj.local_body,
                "district_object": {
                    "id": facility_obj.district.id,
                    "name": facility_obj.district.name,
                    "state": facility_obj.state.id,
                },
                "state_object": {"id": facility_obj.state.id, "name": facility_obj.state.name},
                "facility_type": {
                    "id": facility_obj.facility_type,
                    "name": dict(FACILITY_TYPES)[facility_obj.facility_type],
                },
            }
            referred_to = obj.referred_to.id
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
            "referred_to": referred_to,
            "referred_to_object": referred_to_object,
            "admitted": obj.admitted,
            "admitted_to": obj.admitted_to,
            "admission_date": obj.admission_date,
            "discharge_date": obj.discharge_date,
            "created_date": obj.created_date,
            "modified_date": obj.modified_date,
            "bed_number": obj.bed_number,
        }

    def get_detail_representation(self, obj=None, facility_obj=None) -> dict:
        list_repr = self.get_list_representation(obj, facility_obj=facility_obj)
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

    def test_detail_api_with_referred_to(self):
        consultation = self.create_consultation(referred_to=self.facility)
        response = self.client.get(self.get_url(consultation.id))
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.json(), self.get_detail_representation(consultation, self.facility))
