import json
import os
from datetime import date
from unittest import mock

from django.test import override_settings
from django.urls import reverse
from model_bakery import baker

from care.emr.models.medication_request import MedicationRequestPrescription
from care.emr.resources.medication.request_prescription.spec import (
    MedicationRequestPrescriptionStatus,
)
from care.emr.signals.patient.facility_name_identifier import (
    FacilityPatientNameIdentifierConfig,
)
from care.emr.signals.patient.name_identifier import NameIdentifierConfig
from care.emr.signals.patient.phone_number_identifier import (
    PhoneNumberIdentifierConfig,
)
from care.utils.tests.base import CareAPITestBase
from config.patient_otp_token import PatientToken


@override_settings(
    OTP_QUERYSET_ENABLED=True,
)
class OTPMedicationRequestPrescriptionAPITestCase(CareAPITestBase):
    def setUp(self):
        NameIdentifierConfig.CACHED_CONFIG = {}
        PhoneNumberIdentifierConfig.CACHED_CONFIG = {}
        FacilityPatientNameIdentifierConfig.CACHED_CONFIG = {}
        # Isolate tests from any OTP filter config provided via .env
        env_patcher = mock.patch.dict(os.environ)
        env_patcher.start()
        self.ENV_KEY = "OTP_MEDICATION_REQUEST_PRESCRIPTION_FILTERS"
        os.environ.pop(self.ENV_KEY, None)
        self.addCleanup(env_patcher.stop)
        self.patient = self.create_patient(
            name="Test Patient",
            date_of_birth=date(1990, 1, 1),
            gender="M",
            phone_number="1234567890",
        )
        self.superuser = self.create_super_user()
        self.facility = self.create_facility(user=self.superuser)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility
        )
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.facility_organization,
        )
        token = PatientToken()
        token["phone_number"] = self.patient.phone_number
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token!s}")
        self.url = reverse("otp-medication-prescription-list")
        self.config = [
            {
                "name": "facility",
                "properties": {
                    "lookup_expr": "exact",
                    "field_name": "encounter__facility__external_id",
                },
            },
            {
                "name": "patient",
                "properties": {
                    "lookup_expr": "exact",
                    "field_name": "patient__external_id",
                },
            },
            {
                "name": "encounter",
                "properties": {
                    "lookup_expr": "exact",
                    "field_name": "encounter__external_id",
                },
            },
            {
                "name": "status",
                "properties": {
                    "lookup_expr": "exact",
                    "field_name": "status",
                    "value": "active",
                },
            },
        ]

    def get_detail_url(self, prescription_id):
        return reverse(
            "otp-medication-prescription-detail",
            kwargs={
                "external_id": prescription_id,
            },
        )

    def _create_prescription_obj(self, **kwargs):
        data = {
            "encounter": kwargs.get("encounter", self.encounter),
            "patient": kwargs.get("patient", self.patient),
            "status": kwargs.get(
                "status", MedicationRequestPrescriptionStatus.active.value
            ),
            "name": "Test Prescription",
            "prescribed_by": self.superuser,
        }
        data.update(kwargs)
        return baker.make(MedicationRequestPrescription, **data)

    def set_default_filters(self, config):
        return mock.patch.dict(os.environ, {self.ENV_KEY: json.dumps(config)})

    # List Medication Request Prescriptions related to the OTP Patient
    def test_list_medication_request_prescriptions_with_default_filters(self):
        """
        Test that the list endpoint returns only the prescriptions that match the default filters
        when no query parameters are provided."""
        prescription1 = self._create_prescription_obj(
            status=MedicationRequestPrescriptionStatus.active.value
        )
        self._create_prescription_obj(
            status=MedicationRequestPrescriptionStatus.completed.value
        )
        with self.set_default_filters(self.config):
            response = self.client.get(self.url, format="json")
        self.assertEqual(response.status_code, 200)
        # Only the active prescription should be returned due to default filters
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(prescription1.external_id)
        )

    def test_list_medication_request_prescriptions_with_query_param_override(self):
        """
        Test that the list endpoint returns prescriptions based on query parameters, overriding default filters."""
        self._create_prescription_obj(
            status=MedicationRequestPrescriptionStatus.active.value
        )
        prescription2 = self._create_prescription_obj(
            status=MedicationRequestPrescriptionStatus.completed.value
        )
        with self.set_default_filters(self.config):
            response = self.client.get(
                f"{self.url}?status={MedicationRequestPrescriptionStatus.completed.value}",
                format="json",
            )
        self.assertEqual(response.status_code, 200)
        # The completed prescription should be returned due to query param override
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(prescription2.external_id)
        )

    @override_settings(OTP_QUERYSET_ENABLED=False)
    def test_list_medication_request_prescriptions_otp_query_disabled(self):
        """
        Test that when OTP_QUERYSET_ENABLED is set to False, the list endpoint returns an empty queryset, regardless of default filters or query parameters."""
        self._create_prescription_obj(
            status=MedicationRequestPrescriptionStatus.active.value
        )
        self._create_prescription_obj(
            status=MedicationRequestPrescriptionStatus.completed.value
        )
        with self.set_default_filters(self.config):
            response = self.client.get(self.url, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 0)

    def test_list_medication_request_prescriptions_without_default_filters(self):
        """
        Test that when no default filters are set, the list endpoint returns an empty queryset."""
        self._create_prescription_obj(
            status=MedicationRequestPrescriptionStatus.active.value
        )
        self._create_prescription_obj(
            status=MedicationRequestPrescriptionStatus.completed.value
        )
        response = self.client.get(self.url, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 0)

    def test_list_medication_request_prescriptions_with_invalid_default_filters(self):
        """
        Test that when invalid default filters are set, the list endpoint returns a 400 response with an appropriate error message."""
        self._create_prescription_obj(
            status=MedicationRequestPrescriptionStatus.active.value
        )
        self._create_prescription_obj(
            status=MedicationRequestPrescriptionStatus.completed.value
        )
        invalid_config = [
            {
                "name": "invalid_filter",
                "properties": {
                    "lookup_expr": "exact",
                    "field_name": "invalid_field",
                    "value": "some_value",
                },
            }
        ]
        with self.set_default_filters(invalid_config):
            response = self.client.get(self.url, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["errors"][0]["msg"]["invalid_filter"], "Invalid filter"
        )

    def test_list_medicaition_request_prescriptions_of_a_family_member(self):
        """
        Test that the list endpoint returns only the prescriptions of the authenticated OTP patient and not those of other family members."""
        self._create_prescription_obj(
            status=MedicationRequestPrescriptionStatus.active.value
        )
        # Create a prescription for another patient (family member)
        family_member = self.create_patient(
            name="Family Member",
            date_of_birth=date(1992, 2, 2),
            gender="female",
            phone_number=self.patient.phone_number,  # Same phone number to simulate family member
        )
        family_member_encounter = self.create_encounter(
            patient=family_member,
            facility=self.facility,
            organization=self.facility_organization,
        )
        self._create_prescription_obj()
        family_prescription = self._create_prescription_obj(
            encounter=family_member_encounter,
            patient=family_member,
            status=MedicationRequestPrescriptionStatus.active.value,
        )
        with self.set_default_filters(self.config):
            response = self.client.get(
                self.url, {"patient": str(family_member.external_id)}, format="json"
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(family_prescription.external_id)
        )

    def test_list_medication_request_prescriptions_of_another_patient(self):
        """
        Test that the list endpoint does not return prescriptions of other OTP patients."""
        other_patient = self.create_patient(
            name="Other Patient",
            date_of_birth=date(1993, 3, 3),
            gender="male",
            phone_number="9999999999",
        )
        other_encounter = self.create_encounter(
            patient=other_patient,
            facility=self.facility,
            organization=self.facility_organization,
        )
        self._create_prescription_obj(
            encounter=other_encounter,
            patient=other_patient,
            status=MedicationRequestPrescriptionStatus.active.value,
        )
        with self.set_default_filters(self.config):
            response = self.client.get(
                self.url, {"patient": str(other_patient.external_id)}, format="json"
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 0)

    # Retrieve a specific Medication Request Prescription related to the OTP Patient
    def test_retrieve_medication_request_prescription(self):
        """
        Test that the retrieve endpoint returns the correct prescription for the OTP patient."""
        prescription = self._create_prescription_obj(
            status=MedicationRequestPrescriptionStatus.active.value
        )
        response = self.client.get(
            self.get_detail_url(prescription.external_id), format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(prescription.external_id))

    def test_retrive_medication_request_prescription_of_family_member(self):
        """
        Test that the retrieve endpoint does not return prescriptions of other family members."""
        family_member = self.create_patient(
            name="Family Member",
            date_of_birth=date(1992, 2, 2),
            gender="female",
            phone_number=self.patient.phone_number,  # Same phone number to simulate family member
        )
        family_member_encounter = self.create_encounter(
            patient=family_member,
            facility=self.facility,
            organization=self.facility_organization,
        )
        family_prescription = self._create_prescription_obj(
            encounter=family_member_encounter,
            patient=family_member,
            status=MedicationRequestPrescriptionStatus.active.value,
        )
        response = self.client.get(
            self.get_detail_url(family_prescription.external_id), format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(family_prescription.external_id))

    def test_retrieve_medication_request_prescription_of_another_patient(self):
        """
        Test that the retrieve endpoint does not return prescriptions of other OTP patients."""
        other_patient = self.create_patient(
            name="Other Patient",
            date_of_birth=date(1993, 3, 3),
            gender="male",
            phone_number="9999999999",
        )
        other_encounter = self.create_encounter(
            patient=other_patient,
            facility=self.facility,
            organization=self.facility_organization,
        )
        other_prescription = self._create_prescription_obj(
            encounter=other_encounter,
            patient=other_patient,
            status=MedicationRequestPrescriptionStatus.active.value,
        )
        response = self.client.get(
            self.get_detail_url(other_prescription.external_id), format="json"
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "No MedicationRequestPrescription matches the given query.",
        )

    @override_settings(OTP_QUERYSET_ENABLED=False)
    def test_retrieve_medication_request_prescription_otp_query_disabled(self):
        """
        Test that when OTP_QUERYSET_ENABLED is set to False, the retrieve endpoint returns a 404 response, regardless of the prescription's existence."""
        prescription = self._create_prescription_obj(
            status=MedicationRequestPrescriptionStatus.active.value
        )
        response = self.client.get(
            self.get_detail_url(prescription.external_id), format="json"
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "No MedicationRequestPrescription matches the given query.",
        )
