# flake8: noqa

import pytest

from care.facility.models import Disease, PatientRegistration


@pytest.fixture()
def patient_data():
    return {
        "name": "Foo",
        "age": 40,
        "gender": 1,
        "phone_number": "9998887776",
        "contact_with_carrier": True,
        "medical_history": [{"disease": 1, "details": "Quite bad"}],
    }


@pytest.fixture()
def patient():
    patient = PatientRegistration.objects.create(
        name="Bar", age=31, gender=2, phone_number="7776665554", contact_with_carrier=False
    )
    disease = Disease.objects.create(disease=1, details="Quite bad", patient=patient)
    return patient


@pytest.mark.django_db(transaction=True)
class TestPatient:
    def test_login_required(self, client):
        response = client.post("/api/v1/patient/", {},)
        assert response.status_code == 403

    def test_create(self, client, user, patient_data):
        client.force_authenticate(user=user)
        response = client.post("/api/v1/patient/", patient_data,)
        assert response.status_code == 201
        response = response.json()
        response.pop("id")
        assert response == {
            **patient_data,
            "medical_history": [{"disease": "NO", "details": "Quite bad"}],
            "is_active": True,
            "last_consultation": None,
        }

        patient = PatientRegistration.objects.get(
            name=patient_data["name"],
            age=patient_data["age"],
            gender=patient_data["gender"],
            phone_number=patient_data["phone_number"],
            contact_with_carrier=patient_data["contact_with_carrier"],
            created_by=user,
            is_active=True,
        )
        assert Disease.objects.get(patient=patient, **patient_data["medical_history"][0])

    def test_retrieve(self, client, user, patient):
        client.force_authenticate(user=user)
        patient.created_by = user
        patient.save()
        response = client.get(f"/api/v1/patient/{patient.id}/")
        assert response.status_code == 200
        assert response.json() == {
            "id": patient.id,
            "name": patient.name,
            "age": patient.age,
            "gender": patient.gender,
            "phone_number": patient.phone_number,
            "contact_with_carrier": patient.contact_with_carrier,
            "medical_history": [{"disease": "NO", "details": "Quite bad"}],
            "tele_consultation_history": [],
            "is_active": True,
            "last_consultation": None,
        }

    def test_super_user_access(self, client, user, patient):
        client.force_authenticate(user=user)
        response = client.get(f"/api/v1/patient/{patient.id}/")
        assert response.status_code == 404

        user.is_superuser = True
        user.save()
        response = client.get(f"/api/v1/patient/{patient.id}/")
        assert response.status_code == 200
        assert response.data == {
            "id": patient.id,
            "name": patient.name,
            "age": patient.age,
            "gender": patient.gender,
            "phone_number": patient.phone_number,
            "contact_with_carrier": patient.contact_with_carrier,
            "medical_history": [{"disease": "NO", "details": "Quite bad"}],
            "tele_consultation_history": [],
            "is_active": True,
            "last_consultation": None,
        }

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
                "contact_with_carrier": patient.contact_with_carrier,
                "medical_history": [{"disease": 4, "details": "Mild"}],
            },
        )
        assert response.status_code == 200
        assert response.json() == {
            "id": patient.id,
            "name": patient.name,
            "age": patient.age,
            "gender": patient.gender,
            "phone_number": new_phone_number,
            "contact_with_carrier": patient.contact_with_carrier,
            "medical_history": [
                {"disease": "NO", "details": "Quite bad"},
                {"disease": "HyperTension", "details": "Mild"},
            ],
            "is_active": True,
            "last_consultation": None,
        }
        patient.refresh_from_db()
        assert patient.phone_number == new_phone_number

    def test_destroy(self, client, user, patient):
        client.force_authenticate(user=user)
        patient.created_by = user
        patient.save()

        response = client.delete(f"/api/v1/patient/{patient.id}/",)
        assert response.status_code == 204
        with pytest.raises(PatientRegistration.DoesNotExist):
            PatientRegistration.objects.get(id=patient.id)

    def test_list(self, client, user, patient):
        client.force_authenticate(user=user)
        patient.created_by = user
        patient.save()
        response = client.get(f"/api/v1/patient/")
        assert response.status_code == 200
        assert response.json() == {
            "count": 1,
            "next": None,
            "previous": None,
            "results": [
                {
                    "id": patient.id,
                    "name": patient.name,
                    "age": patient.age,
                    "gender": patient.gender,
                    "phone_number": patient.phone_number,
                    "contact_with_carrier": patient.contact_with_carrier,
                    "medical_history": [{"disease": "NO", "details": "Quite bad"}],
                    "is_active": True,
                    "last_consultation": None,
                },
            ],
        }
