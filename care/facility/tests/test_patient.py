# flake8: noqa

import pytest

from care.facility.models import PatientRegistration


@pytest.fixture()
def patient_data():
    return {
        "name": "Foo",
        "age": 40,
        "gender": 1,
        "phone_number": "9998887776",
        "contact_with_carrier": True,
        "medical_history": {1},
    }


@pytest.fixture()
def patient():
    return PatientRegistration.objects.create(
        name="Bar", age=31, gender=2, phone_number="7776665554", contact_with_carrier=False, medical_history="2,4"
    )


@pytest.mark.django_db(transaction=True)
class TestPatient:
    def test_login_required(self, client):
        response = client.post("/api/v1/patient/", {},)
        assert response.status_code == 403

    def test_create(self, client, user, patient_data):
        client.force_authenticate(user=user)
        response = client.post("/api/v1/patient/", patient_data,)

        assert response.status_code == 201
        response.data.pop("id")
        assert response.data == {
            **patient_data,
            "medical_history_details": None,
            "is_active": True,
            "last_consultation": None,
        }

        assert PatientRegistration.objects.get(
            name=patient_data["name"],
            age=patient_data["age"],
            gender=patient_data["gender"],
            phone_number=patient_data["phone_number"],
            contact_with_carrier=patient_data["contact_with_carrier"],
            medical_history=patient_data["medical_history"],
            medical_history_details=None,
            created_by=user,
            is_active=True,
        )

    def test_retrieve(self, client, user, patient):
        client.force_authenticate(user=user)
        patient.created_by = user
        patient.save()
        response = client.get(f"/api/v1/patient/{patient.id}/")
        assert response.status_code == 200
        assert response.data == {
            "id": patient.id,
            "name": patient.name,
            "age": patient.age,
            "gender": patient.gender,
            "phone_number": patient.phone_number,
            "contact_with_carrier": patient.contact_with_carrier,
            "medical_history": {2, 4},
            "medical_history_details": patient.medical_history_details,
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
            "medical_history": {2, 4},
            "medical_history_details": patient.medical_history_details,
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
                "medical_history": {2, 4},
                "medical_history_details": patient.medical_history_details,
            },
        )
        assert response.status_code == 200
        assert response.data == {
            "id": patient.id,
            "name": patient.name,
            "age": patient.age,
            "gender": patient.gender,
            "phone_number": new_phone_number,
            "contact_with_carrier": patient.contact_with_carrier,
            "medical_history": {2, 4},
            "medical_history_details": patient.medical_history_details,
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
        assert response.data == {
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
                    "medical_history": {2, 4},
                    "medical_history_details": patient.medical_history_details,
                    "is_active": True,
                    "last_consultation": None,
                },
            ],
        }
