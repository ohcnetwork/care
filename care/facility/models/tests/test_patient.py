from care.facility.models import DiseaseStatusEnum, PatientRegistration
from care.users.models import District, State
from care.utils.tests.test_base import TestBase


class PatientRegistrationTest(TestBase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.state = State.objects.create(name="tripura")
        cls.district = District.objects.create(state=cls.state, name="agartala")
        cls.patient_data = cls.get_patient_data(district=cls.district, state=cls.state)
        cls.patient = cls._create_patient(cls.patient_data)

    @classmethod
    def _create_patient(cls, data):
        data = data.copy()
        data.pop("medical_history", [])
        data.pop("state", "")
        data.pop("district", "")
        data.pop("disease_status", 0)
        data.update(
            {"state_id": cls.state.id, "district_id": cls.district.id,}
        )
        return PatientRegistration.objects.create(**data)

    def test_disease_state_recovery_is_aliased_to_recovered(self):
        patient = self.patient

        patient.disease_status = DiseaseStatusEnum.RECOVERY.value
        patient.save(update_fields=["disease_status"])
        patient.refresh_from_db()

        self.assertEqual(patient.disease_status, DiseaseStatusEnum.RECOVERED.value)
