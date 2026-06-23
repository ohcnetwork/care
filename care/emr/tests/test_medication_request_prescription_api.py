from django.urls import reverse
from model_bakery import baker
from rest_framework import status

from care.emr.models.medication_request import MedicationRequestPrescription
from care.emr.resources.medication.request_prescription.spec import (
    MedicationRequestPrescriptionStatus,
)
from care.security.permissions.medication import MedicationPermissions
from care.utils.tests.base import CareAPITestBase


class TestMedicationRequestPrescriptionViewSet(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.superuser = self.create_super_user()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.superuser)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility
        )
        self.patient = self.create_patient()
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.superuser)
        self.base_url = reverse(
            "medication-request-prescription-list",
            kwargs={"patient_external_id": self.patient.external_id},
        )

    def _get_detail_url(self, prescription_id):
        return reverse(
            "medication-request-prescription-detail",
            kwargs={
                "patient_external_id": self.patient.external_id,
                "external_id": prescription_id,
            },
        )

    def _get_prescription_data(self, **overrides):
        data = {
            "status": MedicationRequestPrescriptionStatus.active.value,
            "encounter": str(self.encounter.external_id),
            "prescribed_by": str(self.superuser.external_id),
            "name": "Test Prescription",
            "note": "Test note",
        }
        data.update(overrides)
        return data

    def _create_prescription_obj(self, **kwargs):
        data = {
            "encounter": self.encounter,
            "patient": self.patient,
            "status": MedicationRequestPrescriptionStatus.active.value,
            "name": "Test Prescription",
            "prescribed_by": self.superuser,
        }
        data.update(kwargs)
        return baker.make(MedicationRequestPrescription, **data)

    def test_create_prescription(self):
        data = self._get_prescription_data()
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Test Prescription")
        self.assertEqual(
            response.data["status"],
            MedicationRequestPrescriptionStatus.active.value,
        )

    def test_list_prescriptions(self):
        self._create_prescription_obj()
        self._create_prescription_obj(name="Second Prescription")
        response = self.client.get(
            self.base_url, {"encounter": str(self.encounter.external_id)}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

    def test_retrieve_prescription(self):
        prescription = self._create_prescription_obj()
        url = self._get_detail_url(prescription.external_id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], str(prescription.external_id))

    def test_update_prescription(self):
        prescription = self._create_prescription_obj()
        url = self._get_detail_url(prescription.external_id)
        update_data = {
            "status": MedicationRequestPrescriptionStatus.completed.value,
            "name": "Updated Prescription",
        }
        response = self.client.put(url, update_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["status"],
            MedicationRequestPrescriptionStatus.completed.value,
        )

    def test_filter_by_status(self):
        self._create_prescription_obj(
            status=MedicationRequestPrescriptionStatus.active.value
        )
        self._create_prescription_obj(
            status=MedicationRequestPrescriptionStatus.completed.value
        )
        response = self.client.get(
            self.base_url,
            {
                "status": MedicationRequestPrescriptionStatus.active.value,
                "encounter": str(self.encounter.external_id),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for r in response.data["results"]:
            self.assertEqual(
                r["status"], MedicationRequestPrescriptionStatus.active.value
            )

    def test_filter_by_encounter(self):
        self._create_prescription_obj()
        other_encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.facility_organization,
        )
        self._create_prescription_obj(encounter=other_encounter, patient=self.patient)
        response = self.client.get(
            self.base_url, {"encounter": str(self.encounter.external_id)}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_create_prescription_without_permissions(self):
        self.client.force_authenticate(user=self.user)
        data = self._get_prescription_data()
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_prescription_without_permissions(self):
        prescription = self._create_prescription_obj()
        self.client.force_authenticate(user=self.user)
        url = self._get_detail_url(prescription.external_id)
        update_data = {
            "status": MedicationRequestPrescriptionStatus.completed.value,
            "name": "Updated",
        }
        response = self.client.put(url, update_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_prescription_with_permissions(self):
        prescription = self._create_prescription_obj()
        url = self._get_detail_url(prescription.external_id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], str(prescription.external_id))
        self.assertEqual(response.data["name"], "Test Prescription")

    def test_retrieve_prescription_without_permissions(self):
        prescription = self._create_prescription_obj()
        self.client.force_authenticate(user=self.user)
        url = self._get_detail_url(prescription.external_id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_prescription_with_permissions(self):
        prescription = self._create_prescription_obj()
        url = self._get_detail_url(prescription.external_id)
        update_data = {
            "status": MedicationRequestPrescriptionStatus.completed.value,
            "name": "Updated by Superuser",
        }
        response = self.client.put(url, update_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["status"],
            MedicationRequestPrescriptionStatus.completed.value,
        )


class TestMedicationPrescriptionSummaryViewSet(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.superuser = self.create_super_user()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.superuser)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility
        )
        self.patient = self.create_patient()
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.superuser)
        self.base_url = reverse(
            "medication_prescription-summary",
            kwargs={"facility_external_id": self.facility.external_id},
        )

    def _create_prescription_obj(self, **kwargs):
        data = {
            "encounter": self.encounter,
            "patient": self.patient,
            "status": MedicationRequestPrescriptionStatus.active.value,
            "name": "Test Prescription",
            "prescribed_by": self.superuser,
        }
        data.update(kwargs)
        return baker.make(MedicationRequestPrescription, **data)

    def test_summary_requires_pharmacist_permission(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_summary_as_pharmacist(self):
        pharmacist = self.create_user()
        role = self.create_role_with_permissions(
            permissions=[MedicationPermissions.is_pharmacist.name]
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, pharmacist, role
        )
        self.client.force_authenticate(user=pharmacist)
        self._create_prescription_obj()
        self._create_prescription_obj(name="Second Prescription")
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data["results"]), 2)
