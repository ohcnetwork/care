# flake8: noqa

import pytest
from django.conf import settings

from care.facility.models import Disease, PatientRegistration
from config.tests.helper import mock_equal


@pytest.fixture()
def patient_data():
    return {
        "name": "Foo",
        "age": 40,
        "gender": 1,
        "phone_number": "9998887776",
        "contact_with_confirmed_carrier": True,
        "contact_with_suspected_carrier": False,
        "medical_history": [{"disease": 1, "details": "Quite bad"}],
        "countries_travelled": "Nope",
        "estimated_contact_date": None,
        "has_SARI": False,
        "present_health": "Good",
        "past_travel": False,
        "address": "Elsewhere street, Elsewhere county, Elsewhere",
        "blood_group": None,
        "date_of_return": None,
        "disease_status": "SUSPECTED",
        "number_of_aged_dependents": 0,
        "number_of_chronic_diseased_dependents": 0,
        "ongoing_medication": "",
        "is_medical_worker": False,
    }


@pytest.fixture()
def patient():
    patient = PatientRegistration.objects.create(
        name="Bar", age=31, gender=2, phone_number="7776665554", contact_with_confirmed_carrier=False
    )
    disease = Disease.objects.create(disease=1, details="Quite bad", patient=patient)
    return patient


@pytest.mark.usefixtures("district_data")
@pytest.mark.django_db(transaction=True)
class TestPatient:
    def _response(self, patient):
        return {
            "id": patient.id,
            "name": patient.name,
            "phone_number": patient.phone_number,
            "age": patient.age,
            "gender": patient.gender,
            "contact_with_confirmed_carrier": patient.contact_with_confirmed_carrier,
            "medical_history": [{"disease": "NO", "details": "Quite bad"}],
            "tele_consultation_history": [],
            "is_active": True,
            "last_consultation": None,
            "local_body": None,
            "local_body_object": None,
            "district": None,
            "district_object": None,
            "state": None,
            "state_object": None,
            "facility": mock_equal,
            "facility_object": mock_equal,
            "address": patient.address,
            "contact_with_suspected_carrier": patient.contact_with_suspected_carrier,
            "countries_travelled": patient.countries_travelled,
            "estimated_contact_date": patient.estimated_contact_date,
            "has_SARI": patient.has_SARI,
            "past_travel": patient.past_travel,
            "present_health": patient.present_health,
            "blood_group": None,
            "date_of_return": None,
            "disease_status": "SUSPECTED",
            "number_of_aged_dependents": 0,
            "number_of_chronic_diseased_dependents": 0,
            "ongoing_medication": "",
            "is_medical_worker": patient.is_medical_worker,
        }

    def test_login_required(self, client):
        response = client.post("/api/v1/patient/", {},)
        assert response.status_code == 403

    def test_create(self, client, user, patient_data):
        settings.DEBUG = True
        client.force_authenticate(user=user)
        response = client.post("/api/v1/patient/", patient_data,)
        assert response.status_code == 201
        response = response.json()
        response.pop("id")
        assert response == {
            **patient_data,
            "medical_history": [{"disease": "NO", "details": "Quite bad"}],
            "tele_consultation_history": [],
            "is_active": True,
            "last_consultation": mock_equal,
            "local_body": mock_equal,
            "local_body_object": mock_equal,
            "district": mock_equal,
            "district_object": mock_equal,
            "state": mock_equal,
            "state_object": mock_equal,
            "facility": mock_equal,
            "facility_object": mock_equal,
            "contact_with_suspected_carrier": False,
            "ongoing_medication": "",
        }

        patient = PatientRegistration.objects.get(
            age=patient_data["age"],
            gender=patient_data["gender"],
            contact_with_confirmed_carrier=patient_data["contact_with_confirmed_carrier"],
            created_by=user,
            is_active=True,
        )
        assert patient.name == patient_data["name"]
        assert patient.phone_number == patient_data["phone_number"]
        assert Disease.objects.get(patient=patient, **patient_data["medical_history"][0])

    def test_retrieve(self, client, user, patient):
        client.force_authenticate(user=user)
        patient.created_by = user
        patient.save()
        response = client.get(f"/api/v1/patient/{patient.id}/")
        assert response.status_code == 200
        assert response.json() == self._response(patient)

    def test_super_user_access(self, client, user, patient):
        client.force_authenticate(user=user)
        response = client.get(f"/api/v1/patient/{patient.id}/")
        assert response.status_code == 404

        user.is_superuser = True
        user.save()
        response = client.get(f"/api/v1/patient/{patient.id}/")

        assert response.status_code == 200
        assert response.json() == self._response(patient)

    def test_update(self, client, user, patient):
        client.force_authenticate(user=user)
        patient.created_by = user
        patient.save()

        new_phone_number = "9999997775"
        response = client.put(
            f"/api/v1/patient/{patient.id}/",
            {
                "name": patient.name,
                "age": patient.age,
                "gender": patient.gender,
                "phone_number": new_phone_number,
                "contact_with_confirmed_carrier": patient.contact_with_confirmed_carrier,
                "medical_history": [{"disease": 4, "details": "Mild"}],
            },
        )
        assert response.status_code == 200
        assert response.json() == {
            **self._response(patient),
            "phone_number": new_phone_number,
            "medical_history": [{"details": "Mild", "disease": "HyperTension"}],
        }
        patient.refresh_from_db()
        assert patient.phone_number == new_phone_number

    def test_destroy(self, client, user, patient):
        client.force_authenticate(user=user)
        patient.created_by = user
        patient.save()

        response = client.delete(f"/api/v1/patient/{patient.id}/",)
        assert response.status_code == 403

        user.is_superuser = True
        user.save()
        response = client.delete(f"/api/v1/patient/{patient.id}/",)
        assert response.status_code == 204
        with pytest.raises(PatientRegistration.DoesNotExist):
            PatientRegistration.objects.get(id=patient.id)

    def test_list(self, client, user, patient):
        client.force_authenticate(user=user)
        patient.created_by = user
        patient.save()
        response = client.get(f"/api/v1/patient/?without_facility=true")
        assert response.status_code == 200
        response_payload = {**self._response(patient), "disease_status": "SUSPECTED"}
        for key in ["last_consultation", "medical_history", "tele_consultation_history", "ongoing_medication"]:
            response_payload.pop(key)
        assert response.json() == {
            "count": 1,
            "next": None,
            "previous": None,
            "results": [response_payload,],
        }

        response = client.get(f"/api/v1/patient/")
        assert response.status_code == 200
        assert response.json() == {
            "count": 0,
            "next": None,
            "previous": None,
            "results": [],
        }
