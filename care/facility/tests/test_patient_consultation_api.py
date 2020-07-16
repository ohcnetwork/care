from rest_framework import status

from care.facility.models import FACILITY_TYPES
from care.utils.tests.test_base import TestBase


class TestPatientConsultationApi(TestBase):
    def get_base_url(self):
        return "/api/v1/consultation"

    def get_list_representation_facility(self, facility):
        return {
            "id": str(facility.external_id),
            "name": facility.name,
            "local_body": facility.local_body,
            "district": facility.district.id,
            "state": facility.state.id,
            "local_body_object": facility.local_body,
            "district_object": {
                "id": facility.district.id,
                "name": facility.district.name,
                "state": facility.state.id,
            },
            "state_object": {"id": facility.state.id, "name": facility.state.name},
            "facility_type": {"id": facility.facility_type, "name": dict(FACILITY_TYPES)[facility.facility_type],},
        }

    def get_list_representation(self, obj) -> dict:
        referred_to_object = None
        referred_to = obj.referred_to
        if referred_to:
            referred_to_object = self.get_list_representation_facility(referred_to)
            referred_to = str(obj.referred_to.external_id)
        return {
            "id": str(obj.external_id),
            "patient": str(obj.patient.external_id),
            "facility": str(obj.facility.external_id),
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
            "consultation_notes": obj.consultation_notes,
            "course_in_facility": obj.course_in_facility,
            "discharge_advice": obj.discharge_advice,
            "prescriptions": obj.prescriptions,
            "course_in_facility": obj.course_in_facility,
            "discharge_advice": obj.discharge_advice,
            "prescriptions": obj.prescriptions,
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
        response = self.client.get(self.get_url(str(consultation.external_id)))
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.json(), self.get_detail_representation(consultation))

    def test_detail_api_with_referred_to(self):
        consultation = self.create_consultation(referred_to=self.facility)
        response = self.client.get(self.get_url(str(consultation.external_id)))
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.json(), self.get_detail_representation(consultation))
