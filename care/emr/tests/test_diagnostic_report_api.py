from secrets import choice

from django.urls import reverse

from care.emr.resources.activity_definition.spec import (
    ActivityDefinitionCategoryOptions,
)
from care.emr.resources.diagnostic_report.spec import DiagnosticReportStatusChoices
from care.emr.resources.service_request.spec import (
    ServiceRequestIntentChoices,
    ServiceRequestPriorityChoices,
    ServiceRequestStatusChoices,
)
from care.security.permissions.diagnostic_report import DiagnosticReportPermissions
from care.utils.tests.base import CareAPITestBase


class DiagnosticReportAPITestCases(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.superuser = self.create_super_user()
        self.patient = self.create_patient()
        self.facility = self.create_facility(user=self.user)
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
            intent=choice(list(ServiceRequestIntentChoices)).value,
            priority=choice(list(ServiceRequestPriorityChoices)).value,
            category=choice(list(ActivityDefinitionCategoryOptions)).value,
        )
        self.permission = [
            DiagnosticReportPermissions.can_write_diagnostic_report.name,
            DiagnosticReportPermissions.can_read_diagnostic_report.name,
        ]
        self.url = reverse(
            "diagnostic_report-list",
            kwargs={"patient_external_id": self.patient.external_id},
        )

    def get_detail_url(self, external_id):
        return reverse(
            "diagnostic_report-detail",
            kwargs={
                "patient_external_id": self.patient.external_id,
                "external_id": external_id,
            },
        )

    def generate_diagnostic_report_data(self, **kwargs):
        data = {
            "status": DiagnosticReportStatusChoices.final.value,
            "category": {
                "display": "Laboratory",
                "code": "LAB",
                "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
            },
            "service_request": str(self.service_request.external_id),
        }
        data.update(**kwargs)
        return data
