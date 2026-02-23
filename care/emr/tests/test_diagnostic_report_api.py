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

    # Testcases for creating a diagnostic report

    def test_create_diagnostic_report_as_superuser(self):
        """
        Test that a superuser can create a diagnostic report.
        """
        self.client.force_authenticate(user=self.superuser)
        data = self.generate_diagnostic_report_data()
        response = self.client.post(self.url, data=data, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        get_response = self.client.get(
            self.get_detail_url(external_id=response.data["id"]), format="json"
        )
        self.assertEqual(get_response.status_code, 200, get_response.data)
        self.assertEqual(get_response.data["id"], response.data["id"])
        self.assertEqual(get_response.data["status"], response.data["status"])
        self.assertEqual(
            get_response.data["category"]["code"], response.data["category"]["code"]
        )
        self.assertEqual(
            get_response.data["service_request"]["id"],
            response.data["service_request"]["id"],
        )

    def test_create_diagnostic_report_as_user_with_permissions(self):
        """
        Test that a user with permissions can create a diagnostic report.
        """
        self.client.force_authenticate(user=self.user)
        role = self.create_role_with_permissions(permissions=self.permission)
        self.attach_role_facility_organization_user(
            role=role, user=self.user, facility_organization=self.facility_organization
        )
        data = self.generate_diagnostic_report_data()
        response = self.client.post(self.url, data=data, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        get_response = self.client.get(
            self.get_detail_url(external_id=response.data["id"]), format="json"
        )
        self.assertEqual(get_response.status_code, 200, get_response.data)
        self.assertEqual(get_response.data["id"], response.data["id"])
        self.assertEqual(get_response.data["status"], response.data["status"])
        self.assertEqual(
            get_response.data["category"]["code"], response.data["category"]["code"]
        )
        self.assertEqual(
            get_response.data["service_request"]["id"],
            response.data["service_request"]["id"],
        )

    def test_create_diagnostic_report_as_user_without_permissions(self):
        """
        Test that a user without permissions cannot create a diagnostic report.
        """
        self.client.force_authenticate(user=self.user)
        data = self.generate_diagnostic_report_data()
        response = self.client.post(self.url, data=data, format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(
            response.data["detail"],
            "You do not have permission to write this diagnostic report",
            response.data,
        )

    def test_create_diagnostic_report_with_mismatched_service_request(self):
        """
        Test that creating a diagnostic report with a mismatched service request fails.
        """
        self.client.force_authenticate(user=self.user)
        role = self.create_role_with_permissions(permissions=self.permission)
        self.attach_role_facility_organization_user(
            role=role, user=self.user, facility_organization=self.facility_organization
        )
        another_patient = self.create_patient()
        another_encounter = self.create_encounter(
            patient=another_patient,
            facility=self.facility,
            organization=self.facility_organization,
        )
        another_service_request = self.create_service_request(
            title="Another Service Request",
            patient=another_patient,
            facility=self.facility,
            encounter=another_encounter,
            status=ServiceRequestStatusChoices.active.value,
            intent=choice(list(ServiceRequestIntentChoices)).value,
            priority=choice(list(ServiceRequestPriorityChoices)).value,
            category=choice(list(ActivityDefinitionCategoryOptions)).value,
        )
        data = self.generate_diagnostic_report_data(
            service_request=str(another_service_request.external_id)
        )
        response = self.client.post(self.url, data=data, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "Invalid Request",
            response.data,
        )
