from secrets import choice

from django.urls import reverse
from model_bakery import baker

from care.emr.models.diagnostic_report import DiagnosticReport
from care.emr.models.observation_definition import ObservationDefinition
from care.emr.resources.activity_definition.spec import (
    ActivityDefinitionCategoryOptions,
)
from care.emr.resources.diagnostic_report.spec import DiagnosticReportStatusChoices
from care.emr.resources.questionnaire.spec import SubjectType
from care.emr.resources.service_request.spec import (
    ServiceRequestIntentChoices,
    ServiceRequestPriorityChoices,
    ServiceRequestStatusChoices,
)
from care.security.permissions.diagnostic_report import DiagnosticReportPermissions
from care.security.permissions.patient import PatientPermissions
from care.utils.tests.base import CareAPITestBase


class DiagnosticReportAPITestCases(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.superuser = self.create_super_user()
        self.patient = self.create_patient()
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
            intent=choice(list(ServiceRequestIntentChoices)).value,
            priority=choice(list(ServiceRequestPriorityChoices)).value,
            category=choice(list(ActivityDefinitionCategoryOptions)).value,
        )
        self.permission = [
            DiagnosticReportPermissions.can_write_diagnostic_report.name,
            DiagnosticReportPermissions.can_read_diagnostic_report.name,
            PatientPermissions.can_view_clinical_data.name,
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

    # Testcases for retrieving a diagnostic report

    def test_retrieve_diagnostic_report_as_superuser(self):
        """
        Test that a superuser can retrieve a diagnostic report.
        """

        diagnostic_report = self.create_diagnostic_report()
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.get_detail_url(external_id=diagnostic_report.external_id),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["id"], str(diagnostic_report.external_id))
        self.assertEqual(response.data["status"], diagnostic_report.status)
        self.assertEqual(
            response.data["category"]["code"], diagnostic_report.category["code"]
        )
        self.assertEqual(
            response.data["service_request"]["id"],
            str(diagnostic_report.service_request.external_id),
        )

    def test_retrieve_diagnostic_report_as_user_with_permissions(self):
        """
        Test that a user with permissions can retrieve a diagnostic report.
        """
        diagnostic_report = self.create_diagnostic_report()
        self.client.force_authenticate(user=self.user)
        role = self.create_role_with_permissions(permissions=self.permission)
        self.attach_role_facility_organization_user(
            role=role, user=self.user, facility_organization=self.facility_organization
        )
        response = self.client.get(
            self.get_detail_url(external_id=diagnostic_report.external_id),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["id"], str(diagnostic_report.external_id))
        self.assertEqual(response.data["status"], diagnostic_report.status)
        self.assertEqual(
            response.data["category"]["code"], diagnostic_report.category["code"]
        )
        self.assertEqual(
            response.data["service_request"]["id"],
            str(diagnostic_report.service_request.external_id),
        )

    def test_retrieve_diagnostic_report_as_user_without_permissions(self):
        """
        Test that a user without permissions cannot retrieve a diagnostic report.
        """
        diagnostic_report = self.create_diagnostic_report()
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.get_detail_url(external_id=diagnostic_report.external_id),
            format="json",
        )
        self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(
            response.data["detail"],
            "You do not have permission to read this diagnostic report",
            response.data,
        )

    #  Testcases for listing diagnostic reports

    def test_list_diagnostic_reports_as_superuser(self):
        """
        Test that a superuser can list diagnostic reports.
        """
        diagnostic_report_1 = self.create_diagnostic_report()
        diagnostic_report_2 = self.create_diagnostic_report()
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.url, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data["results"]), 2)
        ids = [report["id"] for report in response.data["results"]]
        self.assertIn(str(diagnostic_report_1.external_id), ids)
        self.assertIn(str(diagnostic_report_2.external_id), ids)

    def test_list_diagnostic_reports_as_user_with_permissions(self):
        """
        Test that a user with permissions can list diagnostic reports.
        """
        diagnostic_report_1 = self.create_diagnostic_report()
        diagnostic_report_2 = self.create_diagnostic_report()
        self.client.force_authenticate(user=self.user)
        role = self.create_role_with_permissions(permissions=self.permission)
        self.attach_role_facility_organization_user(
            role=role, user=self.user, facility_organization=self.facility_organization
        )
        response = self.client.get(self.url, format="json")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data["results"]), 2)
        ids = [report["id"] for report in response.data["results"]]
        self.assertIn(str(diagnostic_report_1.external_id), ids)
        self.assertIn(str(diagnostic_report_2.external_id), ids)

    def test_list_diagnostic_reports_as_user_without_permissions(self):
        """
        Test that a user without permissions cannot list diagnostic reports.
        """
        self.create_diagnostic_report()
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(
            response.data["detail"],
            "You do not have permission to view clinical data for this patient",
            response.data,
        )

    def test_list_diagnostic_reports_with_encounter_filter(self):
        """
        Test that filtering diagnostic reports by encounter works.
        """
        self.create_diagnostic_report()
        another_encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.facility_organization,
        )
        diagnostic_report_2 = self.create_diagnostic_report(encounter=another_encounter)
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            role=self.create_role_with_permissions(permissions=self.permission),
            user=self.user,
            facility_organization=self.facility_organization,
        )
        response = self.client.get(
            self.url + f"?encounter={another_encounter.external_id}", format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(diagnostic_report_2.external_id)
        )

    def test_list_diagnostic_reports_with_service_request_filter(self):
        """
        Test that filtering diagnostic reports by service request works.
        """
        self.create_diagnostic_report()
        another_service_request = self.create_service_request(
            title="Another Service Request",
            patient=self.patient,
            facility=self.facility,
            encounter=self.encounter,
            status=ServiceRequestStatusChoices.active.value,
            intent=choice(list(ServiceRequestIntentChoices)).value,
            priority=choice(list(ServiceRequestPriorityChoices)).value,
            category=choice(list(ActivityDefinitionCategoryOptions)).value,
        )
        diagnostic_report_2 = self.create_diagnostic_report(
            service_request=another_service_request
        )
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            role=self.create_role_with_permissions(permissions=self.permission),
            user=self.user,
            facility_organization=self.facility_organization,
        )
        response = self.client.get(
            self.url + f"?service_request={another_service_request.external_id}",
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(diagnostic_report_2.external_id)
        )

    def test_list_diagnostic_reports_with_unauthorized_encounter_filter(self):
        """
        Test that filtering diagnostic reports by an encounter the user does not have access to fails.
        """
        self.create_diagnostic_report()
        another_encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.facility_organization,
        )
        self.create_diagnostic_report(encounter=another_encounter)
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.url + f"?encounter={another_encounter.external_id}", format="json"
        )
        self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(
            response.data["detail"],
            "You do not have permission to read this diagnostic report in this encounter",
            response.data,
        )

    def test_list_diagnostic_reports_with_unauthorized_service_request_filter(self):
        """
        Test that filtering diagnostic reports by a service request the user does not have access to fails.
        """
        self.create_diagnostic_report()
        another_service_request = self.create_service_request(
            title="Another Service Request",
            patient=self.patient,
            facility=self.facility,
            encounter=self.encounter,
            status=ServiceRequestStatusChoices.active.value,
            intent=choice(list(ServiceRequestIntentChoices)).value,
            priority=choice(list(ServiceRequestPriorityChoices)).value,
            category=choice(list(ActivityDefinitionCategoryOptions)).value,
        )
        self.create_diagnostic_report(service_request=another_service_request)
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.url + f"?service_request={another_service_request.external_id}",
            format="json",
        )
        self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(
            response.data["detail"],
            "You do not have permission to read this diagnostic report for this service request",
            response.data,
        )

    # Testcases for updating a diagnostic report status

    def test_update_diagnostic_report_as_superuser(self):
        """
        Test that a superuser can update a diagnostic report status.
        """
        diagnostic_report = self.create_diagnostic_report()
        self.client.force_authenticate(user=self.superuser)
        data = self.generate_diagnostic_report_data(
            status=DiagnosticReportStatusChoices.final.value
        )

        response = self.client.patch(
            self.get_detail_url(external_id=diagnostic_report.external_id),
            data=data,
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["id"], str(diagnostic_report.external_id))
        self.assertEqual(response.data["status"], data["status"])

    def test_update_diagnostic_report_as_user_with_permissions(self):
        """
        Test that a user with permissions can update a diagnostic report status.
        """
        diagnostic_report = self.create_diagnostic_report()
        self.client.force_authenticate(user=self.user)
        role = self.create_role_with_permissions(permissions=self.permission)
        self.attach_role_facility_organization_user(
            role=role, user=self.user, facility_organization=self.facility_organization
        )
        data = self.generate_diagnostic_report_data(
            status=DiagnosticReportStatusChoices.final.value
        )
        response = self.client.patch(
            self.get_detail_url(external_id=diagnostic_report.external_id),
            data=data,
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["id"], str(diagnostic_report.external_id))
        self.assertEqual(response.data["status"], data["status"])

    def test_update_diagnostic_report_as_user_without_permissions(self):
        """
        Test that a user without permissions cannot update a diagnostic report status.
        """
        diagnostic_report = self.create_diagnostic_report()
        self.client.force_authenticate(user=self.user)
        data = self.generate_diagnostic_report_data(
            status=DiagnosticReportStatusChoices.final.value
        )
        response = self.client.patch(
            self.get_detail_url(external_id=diagnostic_report.external_id),
            data=data,
            format="json",
        )
        self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(
            response.data["detail"],
            "You do not have permission to write this diagnostic report",
            response.data,
        )


class DiagnosticReportUpsertObservationAPITestCases(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.superuser = self.create_super_user()
        self.patient = self.create_patient(year_of_birth=1990)
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
            intent=choice(list(ServiceRequestIntentChoices)).value,
            priority=choice(list(ServiceRequestPriorityChoices)).value,
            category=choice(list(ActivityDefinitionCategoryOptions)).value,
        )
        self.permission = [
            DiagnosticReportPermissions.can_write_diagnostic_report.name,
            DiagnosticReportPermissions.can_read_diagnostic_report.name,
            PatientPermissions.can_view_clinical_data.name,
        ]
        self.diagnostic_report = baker.make(
            DiagnosticReport,
            status=DiagnosticReportStatusChoices.registered.value,
            category={
                "display": "Laboratory",
                "code": "LAB",
                "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
            },
            service_request=self.service_request,
            patient=self.patient,
            encounter=self.encounter,
            facility=self.facility,
        )
        self.observation_definition = baker.make(
            ObservationDefinition,
            facility=self.facility,
            slug="urinalysis-observation",
            code={"code": "LP7681-2", "system": "http://loinc.org", "display": "Urine"},
            category="laboratory",
            permitted_data_type="integer",
            status="active",
            description="Test observation definition",
            qualified_ranges=[
                {
                    "ranges": [
                        {"max": "0.10", "interpretation": {"display": "normal"}}
                    ],
                    "conditions": [
                        {
                            "value": {"max": 120, "min": 0, "value_type": "years"},
                            "metric": "patient_age",
                            "operation": "in_range",
                        }
                    ],
                }
            ],
        )
        self.url = self.get_upsert_url(self.diagnostic_report)

    def get_upsert_url(self, diagnostic_report):
        return reverse(
            "diagnostic_report-upsert-observations",
            kwargs={
                "patient_external_id": self.patient.external_id,
                "external_id": diagnostic_report.external_id,
            },
        )

    def generate_observation_data(self, **kwargs):
        data = {
            "status": "final",
            "value_type": "integer",
            "effective_datetime": "2026-03-09T10:48:52.947Z",
            "value": {"value": "55"},
        }
        data.update(**kwargs)
        return data

    def create_observation(self, **kwargs):
        from care.emr.models.observation import Observation

        data = {
            "status": "final",
            "value_type": "integer",
            "value": {"value": "55"},
            "effective_datetime": "2026-03-09T10:48:52.947Z",
            "diagnostic_report": kwargs.setdefault(
                "diagnostic_report", self.diagnostic_report
            ),
            "encounter": kwargs.setdefault("encounter", self.encounter),
            "patient": kwargs.setdefault("patient", self.patient),
            "subject_type": SubjectType.encounter.value,
            "subject_id": self.encounter.external_id,
            "created_by": kwargs.setdefault("created_by", self.superuser),
        }
        data.update(**kwargs)
        return baker.make(Observation, **data)

    def test_upsert_observation_with_definition_as_superuser(self):
        """
        Test that a superuser can upsert an observation using an observation definition.
        """
        self.client.force_authenticate(user=self.superuser)
        data = {
            "observations": [
                {
                    "observation_definition": self.observation_definition.slug,
                    "observation": self.generate_observation_data(),
                }
            ]
        }
        response = self.client.post(self.url, data=data, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["message"], "Observations updated successfully")

    def test_upsert_observation_with_definition_as_user_with_permissions(self):
        """
        Test that a user with permissions can upsert an observation using an observation definition.
        """
        self.client.force_authenticate(user=self.user)
        role = self.create_role_with_permissions(permissions=self.permission)
        self.attach_role_facility_organization_user(
            role=role, user=self.user, facility_organization=self.facility_organization
        )
        data = {
            "observations": [
                {
                    "observation_definition": self.observation_definition.slug,
                    "observation": self.generate_observation_data(),
                }
            ]
        }
        response = self.client.post(self.url, data=data, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["message"], "Observations updated successfully")

    def test_upsert_observation_with_definition_as_user_without_permissions(self):
        """
        Test that a user without permissions cannot upsert observations.
        """
        self.client.force_authenticate(user=self.user)
        data = {
            "observations": [
                {
                    "observation_definition": self.observation_definition.slug,
                    "observation": self.generate_observation_data(),
                }
            ]
        }
        response = self.client.post(self.url, data=data, format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(
            response.data["detail"],
            "You do not have permission to write this diagnostic report",
            response.data,
        )

    def test_upsert_bare_observation_as_superuser(self):
        """
        Test that a superuser can upsert a bare observation (no definition, no id).
        """
        self.client.force_authenticate(user=self.superuser)
        data = {
            "observations": [
                {
                    "observation": self.generate_observation_data(),
                }
            ]
        }
        response = self.client.post(self.url, data=data, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["message"], "Observations updated successfully")

    def test_upsert_update_existing_observation_as_superuser(self):
        """
        Test that a superuser can update an existing observation via observation_id.
        """
        self.client.force_authenticate(user=self.superuser)

        observation = self.create_observation()
        data = {
            "observations": [
                {
                    "observation_id": str(observation.external_id),
                    "observation": self.generate_observation_data(
                        value={"value": "99"}
                    ),
                }
            ]
        }
        response = self.client.post(self.url, data=data, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["message"], "Observations updated successfully")
        observation.refresh_from_db()
        self.assertEqual(observation.value, {"value": "99"})

    def test_upsert_observation_on_final_diagnostic_report(self):
        """
        Test that upserting observations on a final diagnostic report is rejected.
        """
        self.client.force_authenticate(user=self.superuser)
        self.diagnostic_report.status = DiagnosticReportStatusChoices.final.value
        self.diagnostic_report.save(update_fields=["status"])
        data = {
            "observations": [
                {
                    "observation_definition": self.observation_definition.slug,
                    "observation": self.generate_observation_data(),
                }
            ]
        }
        response = self.client.post(self.url, data=data, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn(
            "Cannot update observations for a final diagnostic report",
            str(response.data),
        )

    def test_upsert_multiple_observations_as_superuser(self):
        """
        Test that a superuser can upsert multiple observations in a single request.
        """
        self.client.force_authenticate(user=self.superuser)
        data = {
            "observations": [
                {
                    "observation_definition": self.observation_definition.slug,
                    "observation": self.generate_observation_data(
                        value={"value": "10"}
                    ),
                },
                {
                    "observation": self.generate_observation_data(
                        value={"value": "20"}
                    ),
                },
            ]
        }
        response = self.client.post(self.url, data=data, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["message"], "Observations updated successfully")

    def test_upsert_observation_with_invalid_definition(self):
        """
        Test that upserting with a non-existent observation definition returns 404.
        """
        self.client.force_authenticate(user=self.superuser)
        data = {
            "observations": [
                {
                    "observation_definition": "non-existent-slug",
                    "observation": self.generate_observation_data(),
                }
            ]
        }
        response = self.client.post(self.url, data=data, format="json")
        self.assertEqual(response.status_code, 404, response.data)
