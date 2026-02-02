from django.urls import reverse
from model_bakery import baker

from care.emr.models import DiagnosticReport, ServiceRequest
from care.emr.models.observation_definition import ObservationDefinition
from care.emr.resources.diagnostic_report.spec import DiagnosticReportStatusChoices
from care.security.permissions.diagnostic_report import DiagnosticReportPermissions
from care.utils.tests.base import CareAPITestBase


class TestDiagnosticReportUpsertObservationsViewSet(CareAPITestBase):
    """Tests for DiagnosticReport upsert_observations endpoint."""

    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.patient = self.create_patient()
        self.client.force_authenticate(user=self.user)

        # Create encounter
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
            status=None,
        )

        # Create service request (required for diagnostic report)
        self.service_request = baker.make(
            ServiceRequest,
            patient=self.patient,
            facility=self.facility,
            encounter=self.encounter,
        )

        # Create diagnostic report
        self.diagnostic_report = baker.make(
            DiagnosticReport,
            patient=self.patient,
            facility=self.facility,
            encounter=self.encounter,
            service_request=self.service_request,
            status=DiagnosticReportStatusChoices.partial.value,
        )

        # Create observation definition with qualified_ranges for interpretation
        # Using empty conditions to avoid patient age check which requires date_of_birth
        self.observation_definition = baker.make(
            ObservationDefinition,
            facility=self.facility,
            slug="test-creatinine",
            title="Creatinine",
            status="active",
            description="Serum Creatinine Test",
            derived_from_uri="",
            category="laboratory",
            code={
                "code": "2160-0",
                "system": "http://loinc.org",
                "display": "Creatinine",
            },
            permitted_data_type="quantity",
            qualified_ranges=[
                {
                    "conditions": [],
                    "ranges": [
                        {"interpretation": {"display": "low"}, "max": "0.4"},
                        {
                            "interpretation": {"display": "normal"},
                            "max": "1.4",
                            "min": "0.4",
                        },
                        {"interpretation": {"display": "high"}, "min": "1.4"},
                    ],
                }
            ],
        )

        # Set up permissions
        permissions = [DiagnosticReportPermissions.can_write_diagnostic_report.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        self.upsert_url = reverse(
            "diagnostic_report-upsert-observations",
            kwargs={
                "patient_external_id": self.patient.external_id,
                "external_id": self.diagnostic_report.external_id,
            },
        )

    def _build_observation_payload(
        self, value, value_type="quantity", unit_code="mg/dL", coding=None
    ):
        """Helper to build observation payload with given value and type."""
        value_obj = {"value": value}

        if value_type == "quantity":
            value_obj["unit"] = {
                "code": unit_code,
                "system": "http://example.system.com",
                "display": unit_code,
            }

        if coding:
            value_obj["coding"] = coding

        return {
            "observations": [
                {
                    "observation": {
                        "effective_datetime": "2026-01-31T03:08:44.827Z",
                        "status": "final",
                        "value": value_obj,
                        "value_type": value_type,
                    },
                    "observation_definition": self.observation_definition.slug,
                }
            ]
        }

    def test_upsert_observations_with_valid_decimal_value(self):
        payload = self._build_observation_payload("1.0")
        response = self.client.post(self.upsert_url, payload, format="json")
        self.assertEqual(response.status_code, 200, response.json())
        self.assertEqual(
            response.json()["message"], "Observations updated successfully"
        )

    def test_upsert_observations_with_invalid_decimal_dot_only(self):
        payload = self._build_observation_payload(".")
        response = self.client.post(self.upsert_url, payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_upsert_observations_with_invalid_decimal_less_than_symbol(self):
        payload = self._build_observation_payload("<0.001")
        response = self.client.post(self.upsert_url, payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_upsert_observations_with_invalid_decimal_greater_than_symbol(self):
        payload = self._build_observation_payload(">100")
        response = self.client.post(self.upsert_url, payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_upsert_observations_with_quoted_value(self):
        payload = self._build_observation_payload("'134'")
        response = self.client.post(self.upsert_url, payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_upsert_observations_with_empty_string(self):
        payload = self._build_observation_payload("")
        response = self.client.post(self.upsert_url, payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_upsert_observations_with_text_value(self):
        payload = self._build_observation_payload("positive")

        response = self.client.post(self.upsert_url, payload, format="json")

        self.assertEqual(response.status_code, 400)

    def test_upsert_observations_with_whitespace_value(self):
        payload = self._build_observation_payload("   ")
        response = self.client.post(self.upsert_url, payload, format="json")
        self.assertEqual(response.status_code, 400)

    # ==================== Valid Numeric Values ====================

    def test_upsert_observations_with_valid_integer_value(self):
        payload = self._build_observation_payload("134")
        response = self.client.post(self.upsert_url, payload, format="json")
        self.assertEqual(response.status_code, 200, response.json())

    def test_upsert_observations_with_valid_negative_value(self):
        payload = self._build_observation_payload("-5.5")
        response = self.client.post(self.upsert_url, payload, format="json")
        self.assertEqual(response.status_code, 200, response.json())

    def test_upsert_observations_with_valid_zero_value(self):
        payload = self._build_observation_payload("0")
        response = self.client.post(self.upsert_url, payload, format="json")
        self.assertEqual(response.status_code, 200, response.json())

    def test_upsert_observations_with_valid_large_decimal_value(self):
        payload = self._build_observation_payload("12345.67890")
        response = self.client.post(self.upsert_url, payload, format="json")
        self.assertEqual(response.status_code, 200, response.json())

    def test_upsert_observations_with_valid_leading_zero_decimal(self):
        payload = self._build_observation_payload("0.001")
        response = self.client.post(self.upsert_url, payload, format="json")
        self.assertEqual(response.status_code, 200, response.json())
