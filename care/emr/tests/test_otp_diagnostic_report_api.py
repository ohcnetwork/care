import json
import os
from datetime import date
from unittest import mock

from django.test import override_settings
from django.urls import reverse
from model_bakery import baker

from care.emr.models.diagnostic_report import DiagnosticReport
from care.emr.resources.activity_definition.spec import (
    ActivityDefinitionCategoryOptions,
)
from care.emr.resources.diagnostic_report.spec import DiagnosticReportStatusChoices
from care.emr.resources.service_request.spec import (
    ServiceRequestIntentChoices,
    ServiceRequestPriorityChoices,
    ServiceRequestStatusChoices,
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
class OTPDiagnosticReportAPITestCase(CareAPITestBase):
    def setUp(self):
        NameIdentifierConfig.CACHED_CONFIG = {}
        PhoneNumberIdentifierConfig.CACHED_CONFIG = {}
        FacilityPatientNameIdentifierConfig.CACHED_CONFIG = {}
        env_patcher = mock.patch.dict(os.environ)
        env_patcher.start()
        self.ENV_KEY = "OTP_DIAGNOSTIC_REPORT_FILTERS"
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
        self.service_request = self.create_service_request(
            title="Test Service Request",
            patient=self.patient,
            facility=self.facility,
            encounter=self.encounter,
            status=ServiceRequestStatusChoices.active.value,
            intent=ServiceRequestIntentChoices.order.value,
            priority=ServiceRequestPriorityChoices.routine.value,
            category=ActivityDefinitionCategoryOptions.laboratory.value,
        )
        token = PatientToken()
        token["phone_number"] = self.patient.phone_number
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token!s}")
        self.url = reverse("otp-diagnostic-report-list")
        self.config = [
            {
                "name": "status",
                "properties": {
                    "lookup_expr": "exact",
                    "field_name": "status",
                    "value": DiagnosticReportStatusChoices.final.value,
                },
            }
        ]

    def get_detail_url(self, diagnostic_report_id):
        return reverse(
            "otp-diagnostic-report-detail", kwargs={"external_id": diagnostic_report_id}
        )

    def create_diagnostic_report(self, **kwargs):
        data = {
            "status": DiagnosticReportStatusChoices.final.value,
            "category": {
                "display": "Laboratory",
                "code": "LAB",
                "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
            },
            "service_request": kwargs.setdefault(
                "service_request", self.service_request
            ),
            "patient": kwargs.setdefault("patient", self.patient),
            "encounter": kwargs.setdefault("encounter", self.encounter),
            "facility": kwargs.setdefault("facility", self.facility),
        }
        data.update(**kwargs)
        return baker.make(DiagnosticReport, **data)

    def set_default_filters(self, config):
        return mock.patch.dict(os.environ, {self.ENV_KEY: json.dumps(config)})

    # List Diagnostic Reports related to the OTP Patient
    def test_list_diagnostic_reports_with_default_filters(self):
        diagnostic_report1 = self.create_diagnostic_report(
            status=DiagnosticReportStatusChoices.final.value
        )
        self.create_diagnostic_report(
            status=DiagnosticReportStatusChoices.preliminary.value
        )
        with self.set_default_filters(self.config):
            response = self.client.get(self.url, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(diagnostic_report1.external_id)
        )

    @override_settings(OTP_QUERYSET_ENABLED=False)
    def test_list_diagnostic_reports_otp_query_disabled(self):
        self.create_diagnostic_report(status=DiagnosticReportStatusChoices.final.value)
        self.create_diagnostic_report(
            status=DiagnosticReportStatusChoices.preliminary.value
        )
        response = self.client.get(self.url, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 0)

    def test_list_diagnostic_reports_without_default_filters(self):
        self.create_diagnostic_report(status=DiagnosticReportStatusChoices.final.value)
        self.create_diagnostic_report(
            status=DiagnosticReportStatusChoices.preliminary.value
        )
        response = self.client.get(self.url, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 0)

    def test_list_diagnostic_reports_with_invalid_default_filters(self):
        self.create_diagnostic_report(status=DiagnosticReportStatusChoices.final.value)
        self.create_diagnostic_report(
            status=DiagnosticReportStatusChoices.preliminary.value
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

    def test_list_diagnostic_reports_with_override_default_filter(self):
        self.create_diagnostic_report(status=DiagnosticReportStatusChoices.final.value)
        diagnostic_report2 = self.create_diagnostic_report(
            status=DiagnosticReportStatusChoices.preliminary.value
        )
        with self.set_default_filters(self.config):
            response = self.client.get(
                f"{self.url}?status={DiagnosticReportStatusChoices.preliminary.value}",
                format="json",
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(diagnostic_report2.external_id)
        )

    # Retrieve a specific Diagnostic Report related to the OTP Patient
    def test_retrieve_diagnostic_report(self):
        diagnostic_report = self.create_diagnostic_report(
            status=DiagnosticReportStatusChoices.preliminary.value
        )
        response = self.client.get(
            self.get_detail_url(diagnostic_report.external_id), format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(diagnostic_report.external_id))

    @override_settings(OTP_QUERYSET_ENABLED=False)
    def test_retrieve_diagnostic_report_without_queryset_disabled(self):
        diagnostic_report = self.create_diagnostic_report(
            status=DiagnosticReportStatusChoices.preliminary.value
        )
        response = self.client.get(
            self.get_detail_url(diagnostic_report.external_id), format="json"
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "No DiagnosticReport matches the given query.",
        )
