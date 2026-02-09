from django.urls import reverse

from care.security.permissions.encounter import EncounterPermissions
from care.security.permissions.patient import PatientPermissions
from care.security.permissions.questionnaire import QuestionnairePermissions
from care.utils.tests.base import CareAPITestBase


class BatchRequestAPITest(CareAPITestBase):
    def setUp(self):
        self.superuser = self.create_super_user(username="admin")
        self.user = self.create_user(username="user")
        self.facility = self.create_facility(name="Test Facility", user=self.superuser)
        self.organization = self.create_organization(
            name="Test Organization", org_type="Role"
        )
        self.facility_organization = self.create_facility_organization(
            facility=self.facility,
        )
        self.patient = self.create_patient()
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.facility_organization,
        )
        self.url = reverse("batch-requests-list")

    def create_batch_request(self, requests, user=None):
        from rest_framework_simplejwt.tokens import RefreshToken

        auth_user = user if user else self.superuser
        refresh = RefreshToken.for_user(auth_user)
        token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return self.client.post(self.url, data={"requests": requests}, format="json")

    def create_request(self, url, method, body=None, reference_id=None, **kwargs):
        request = {
            "url": url,
            "method": method,
        }
        if body:
            request["body"] = body
        if reference_id:
            request["reference_id"] = reference_id
        if kwargs.get("replacements"):
            request["replacements"] = kwargs.get("replacements")
        return request


class QuestionnaireBatchRequestAPITest(BatchRequestAPITest):
    def setUp(self):
        super().setUp()
        self.questionnaire = self.create_questionnaire()
        self.questionnaire_url = reverse("questionnaire-list")
        self.add_questionnaire_organization()

    def create_questionnaire(self):
        from care.emr.models.questionnaire import Questionnaire

        return Questionnaire.objects.create(
            title="TestQuestionnaire",
            slug="testquestionnaire",
            description="",
            questions=[
                {
                    "id": "889833b0-68a2-4f5a-bf54-619b93b3cb73",
                    "text": "Unstuctured Question",
                    "type": "string",
                    "link_id": "Q-1770085511226",
                },
                {
                    "id": "50fe267c-3818-4c70-9cd5-91745902042d",
                    "text": "Structured Question Allergy",
                    "type": "structured",
                    "link_id": "Q-1770085550092",
                    "repeats": False,
                    "structured_type": "allergy_intolerance",
                },
                {
                    "id": "dce46e21-eca9-4b21-a353-6b74b1a0b998",
                    "text": "Structured Question Diagnosis",
                    "type": "structured",
                    "link_id": "Q-1770085586498",
                    "repeats": False,
                    "structured_type": "diagnosis",
                },
            ],
            status="active",
            subject_type="encounter",
            version="0.1",
        )

    def add_questionnaire_organization(self):
        self.client.force_authenticate(user=self.superuser)
        data = {
            "organizations": [self.organization.external_id],
        }
        response = self.client.post(
            reverse("questionnaire-set-organizations", args=[self.questionnaire.slug]),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)

    def generate_request_payload(self, patient, encounter):
        return [
            {
                "url": f"/api/v1/patient/{patient}/allergy_intolerance/upsert/",
                "method": "POST",
                "body": {
                    "datapoints": [
                        {
                            "code": {
                                "code": "50020101000188103",
                                "display": "Benzenesulfonic acid",
                                "system": "http://snomed.info/sct",
                            },
                            "clinical_status": "active",
                            "verification_status": "confirmed",
                            "category": "medication",
                            "criticality": "low",
                            "encounter": encounter,
                        },
                        {
                            "code": {
                                "code": "842825221000119100",
                                "display": "Anifrolumab",
                                "system": "http://snomed.info/sct",
                            },
                            "clinical_status": "active",
                            "verification_status": "confirmed",
                            "category": "medication",
                            "criticality": "low",
                            "encounter": encounter,
                        },
                        {
                            "code": {
                                "code": "3577911000001100",
                                "display": "Purified water",
                                "system": "http://snomed.info/sct",
                            },
                            "clinical_status": "active",
                            "verification_status": "confirmed",
                            "category": "medication",
                            "criticality": "low",
                            "encounter": encounter,
                        },
                        {
                            "code": {
                                "code": "42544811000001108",
                                "display": "Fezolinetant",
                                "system": "http://snomed.info/sct",
                            },
                            "clinical_status": "active",
                            "verification_status": "confirmed",
                            "category": "medication",
                            "criticality": "low",
                            "encounter": encounter,
                        },
                    ]
                },
                "reference_id": "allergy_intolerance",
            },
            {
                "url": f"/api/v1/patient/{patient}/diagnosis/upsert/",
                "method": "POST",
                "body": {
                    "datapoints": [
                        {
                            "code": {
                                "code": "972604701000119104",
                                "display": "Acquired arteriovenous malformation of vascular structure of gastrointestinal tract",
                                "system": "http://snomed.info/sct",
                            },
                            "clinical_status": "active",
                            "verification_status": "confirmed",
                            "severity": "moderate",
                            "category": "encounter_diagnosis",
                            "onset": {"onset_datetime": "2026-02-03"},
                            "encounter": encounter,
                        },
                        {
                            "code": {
                                "code": "969688801000119108",
                                "display": "Acute left-sided ulcerative colitis",
                                "system": "http://snomed.info/sct",
                            },
                            "clinical_status": "active",
                            "verification_status": "confirmed",
                            "severity": "moderate",
                            "category": "encounter_diagnosis",
                            "onset": {"onset_datetime": "2026-02-03"},
                            "encounter": encounter,
                        },
                        {
                            "code": {
                                "code": "971608291000119105",
                                "display": "Venous ulcer of left ankle",
                                "system": "http://snomed.info/sct",
                            },
                            "clinical_status": "active",
                            "verification_status": "confirmed",
                            "severity": "moderate",
                            "category": "encounter_diagnosis",
                            "onset": {"onset_datetime": "2026-02-03"},
                            "encounter": encounter,
                        },
                        {
                            "code": {
                                "code": "971918681000119107",
                                "display": "Chronic respiratory failure due to obstructive sleep apnoea",
                                "system": "http://snomed.info/sct",
                            },
                            "clinical_status": "active",
                            "verification_status": "confirmed",
                            "severity": "moderate",
                            "category": "encounter_diagnosis",
                            "onset": {"onset_datetime": "2026-02-03"},
                            "encounter": encounter,
                        },
                    ]
                },
                "reference_id": "diagnosis",
            },
            {
                "url": "/api/v1/questionnaire/testquestionnaire/submit/",
                "method": "POST",
                "reference_id": "26cf708d-c8b1-4c2b-8995-36d2eb88622e",
                "body": {
                    "resource_id": encounter,
                    "encounter": encounter,
                    "patient": patient,
                    "results": [
                        {
                            "question_id": "889833b0-68a2-4f5a-bf54-619b93b3cb73",
                            "values": [{"value": "Test response"}],
                        }
                    ],
                },
            },
        ]

    def test_questionnaire_batch_request(self):
        """
        Test creating a batch request with questionnaire submission along with
        strucured data types like allergy and diagnosis.
        """
        requests = self.generate_request_payload(
            self.patient.external_id, self.encounter.external_id
        )
        response = self.create_batch_request(requests=requests)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 3)
        refernce_ids = [req["reference_id"] for req in response.data["results"]]
        self.assertIn("allergy_intolerance", refernce_ids)
        self.assertIn("diagnosis", refernce_ids)
        self.assertIn("26cf708d-c8b1-4c2b-8995-36d2eb88622e", refernce_ids)
        for result in response.data["results"]:
            self.assertEqual(result["status_code"], 200)

    def test_questionnaire_batch_request_without_permission(self):
        """
        Test creating a batch request with questionnaire submission without
        proper organization permission.
        """
        self.client.force_authenticate(user=self.user)
        requests = self.generate_request_payload(
            self.patient.external_id, self.encounter.external_id
        )
        response = self.create_batch_request(requests=requests, user=self.user)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(response.data["results"]), 3)
        for result in response.data["results"]:
            if result["reference_id"] == "26cf708d-c8b1-4c2b-8995-36d2eb88622e":
                self.assertEqual(result["status_code"], 404)
            else:
                self.assertEqual(result["status_code"], 400)

    def test_questionnaire_batch_request_partial_failure(self):
        """
        Test creating a batch request with questionnaire submission where one of the
        requests fail.
        """
        self.client.force_authenticate(user=self.user)
        requests = self.generate_request_payload(
            self.patient.external_id, self.encounter.external_id
        )
        self.permission = [
            EncounterPermissions.can_submit_encounter_questionnaire.name,
            EncounterPermissions.can_write_encounter_clinical_data.name,
            QuestionnairePermissions.can_read_questionnaire.name,
            PatientPermissions.can_write_patient.name,
            EncounterPermissions.can_write_encounter.name,
        ]
        self.role = self.create_role_with_permissions(
            role_name="Test Role",
            permissions=self.permission,
        )
        self.attach_role_facility_organization_user(
            user=self.user,
            facility_organization=self.facility_organization,
            role=self.role,
        )
        response = self.create_batch_request(requests=requests, user=self.user)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(response.data["results"]), 3)
        refernce_ids = [req["reference_id"] for req in response.data["results"]]
        self.assertIn("allergy_intolerance", refernce_ids)
        self.assertIn("diagnosis", refernce_ids)
        self.assertIn("26cf708d-c8b1-4c2b-8995-36d2eb88622e", refernce_ids)
        for result in response.data["results"]:
            if result["reference_id"] == "26cf708d-c8b1-4c2b-8995-36d2eb88622e":
                self.assertEqual(result["status_code"], 404)
            else:
                self.assertEqual(result["status_code"], 200)

    def test_questionnaire_batch_request_with_permission(self):
        """
        Test creating a batch request with questionnaire submission with
        proper organization permission.
        """
        self.client.force_authenticate(user=self.user)
        requests = self.generate_request_payload(
            self.patient.external_id, self.encounter.external_id
        )
        self.permission = [
            EncounterPermissions.can_submit_encounter_questionnaire.name,
            EncounterPermissions.can_write_encounter_clinical_data.name,
            QuestionnairePermissions.can_read_questionnaire.name,
            QuestionnairePermissions.can_write_questionnaire.name,
            PatientPermissions.can_write_patient.name,
            EncounterPermissions.can_write_encounter.name,
        ]
        self.role = self.create_role_with_permissions(
            role_name="Test Role",
            permissions=self.permission,
        )
        self.attach_role_facility_organization_user(
            user=self.user,
            facility_organization=self.facility_organization,
            role=self.role,
        )
        self.attach_role_organization_user(
            user=self.user,
            organization=self.organization,
            role=self.role,
        )
        response = self.create_batch_request(requests=requests, user=self.user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 3)
        refernce_ids = [req["reference_id"] for req in response.data["results"]]
        self.assertIn("allergy_intolerance", refernce_ids)
        self.assertIn("diagnosis", refernce_ids)
        self.assertIn("26cf708d-c8b1-4c2b-8995-36d2eb88622e", refernce_ids)
        for result in response.data["results"]:
            self.assertEqual(result["status_code"], 200)

    def test_questionnaire_batch_request_invalid_payload(self):
        """
        Test creating a batch request with invalid payload.
        """
        requests = [
            {
                "url": f"/api/v1/patient/{self.patient.external_id}/allergy_intolerance/upsert/",
                "method": "POST",
                "body": {"datapoints": "invalid_datapoints"},
                "reference_id": "allergy_intolerance",
            }
        ]
        response = self.create_batch_request(requests=requests)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["reference_id"], "allergy_intolerance"
        )
        self.assertEqual(response.data["results"][0]["status_code"], 400)

    def test_questionnaire_batch_request_empty_requests(self):
        """
        Test creating a batch request with empty requests list.
        """
        requests = []
        response = self.create_batch_request(requests=requests)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            f"List should have at least 1 item after validation, not {len(requests)}",
        )

    def test_questionnaire_batch_request_exceed_max_requests(self):
        """
        Test creating a batch request exceeding maximum allowed requests.
        """
        max_requests = 20
        requests = [
            {
                "url": f"/api/v1/patient/{self.patient.external_id}/allergy_intolerance/upsert/",
                "method": "POST",
                "body": {"datapoints": []},
                "reference_id": f"allergy_intolerance_{i}",
            }
            for i in range(max_requests + 1)
        ]
        response = self.create_batch_request(requests=requests)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            f"List should have at most {max_requests} items after validation, not {len(requests)}",
        )


class ReplacementBatchRequestAPITest(QuestionnaireBatchRequestAPITest):
    def setUp(self):
        super().setUp()

    def test_batch_request_with_replacement_as_superuser(self):
        """
        Test creating a batch request with replacement details on
        fetching the patient and create encounter for that patient.
        """
        patient_request = self.create_request(
            url=reverse("patient-detail", args=[self.patient.external_id]),
            method="GET",
            reference_id="patient_fetch",
        )
        encounter_request = self.create_request(
            url=reverse("encounter-list"),
            method="POST",
            body={
                "patient": None,
                "facility": self.facility.external_id,
                "organizations": [str(self.facility_organization.external_id)],
                "encounter_class": "imp",
                "status": "planned",
                "priority": "routine",
            },
            reference_id="encounter_create",
            replacements=[
                {
                    "source_path": {"reference_id": "patient_fetch", "path": "id"},
                    "value_path": {
                        "reference_id": "encounter_create",
                        "path": "patient",
                    },
                }
            ],
        )
        requests = [patient_request, encounter_request]
        response = self.create_batch_request(requests=requests)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        for result in response.data["results"]:
            self.assertEqual(result["status_code"], 200)
        encounter_data = next(
            (
                res
                for res in response.data["results"]
                if res["reference_id"] == "encounter_create"
            ),
            None,
        )
        self.assertIsNotNone(encounter_data)
        self.assertEqual(
            encounter_data["data"]["patient"]["id"], str(self.patient.external_id)
        )

    def test_batch_request_with_replacement_with_partial_permission(self):
        """
        Test creating a batch request with replacement details on
        fetching the patient and create encounter for that patient
        without proper permissions.
        """
        patient_request = self.create_request(
            url=reverse("patient-detail", args=[self.patient.external_id]),
            method="GET",
            reference_id="patient_fetch",
        )
        encounter_request = self.create_request(
            url=reverse("encounter-list"),
            method="POST",
            body={
                "patient": None,
                "facility": self.facility.external_id,
                "organizations": [str(self.facility_organization.external_id)],
                "encounter_class": "imp",
                "status": "planned",
                "priority": "routine",
            },
            reference_id="encounter_create",
            replacements=[
                {
                    "source_path": {"reference_id": "patient_fetch", "path": "id"},
                    "value_path": {
                        "reference_id": "encounter_create",
                        "path": "patient",
                    },
                }
            ],
        )
        requests = [patient_request, encounter_request]
        self.permission = [
            PatientPermissions.can_view_clinical_data.name,
        ]
        self.role = self.create_role_with_permissions(
            role_name="Test Role",
            permissions=self.permission,
        )
        self.attach_role_facility_organization_user(
            user=self.user,
            facility_organization=self.facility_organization,
            role=self.role,
        )
        response = self.create_batch_request(requests=requests, user=self.user)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(response.data["results"]), 2)
        for result in response.data["results"]:
            if result["reference_id"] == "patient_fetch":
                self.assertEqual(result["status_code"], 200)
            else:
                self.assertEqual(result["status_code"], 403)

    def test_batch_request_with_replacement_with_permission(self):
        """
        Test creating a batch request with replacement details on
        fetching the patient and create encounter for that patient
        with proper permissions.
        """
        patient_request = self.create_request(
            url=reverse("patient-detail", args=[self.patient.external_id]),
            method="GET",
            reference_id="patient_fetch",
        )
        encounter_request = self.create_request(
            url=reverse("encounter-list"),
            method="POST",
            body={
                "patient": None,
                "facility": self.facility.external_id,
                "organization": [str(self.facility_organization.external_id)],
                "encounter_class": "imp",
                "status": "planned",
                "priority": "routine",
            },
            reference_id="encounter_create",
            replacements=[
                {
                    "source_path": {"reference_id": "patient_fetch", "path": "id"},
                    "value_path": {
                        "reference_id": "encounter_create",
                        "path": "patient",
                    },
                }
            ],
        )
        requests = [patient_request, encounter_request]
        self.permission = [
            PatientPermissions.can_view_clinical_data.name,
            EncounterPermissions.can_create_encounter.name,
        ]
        self.role = self.create_role_with_permissions(
            role_name="Test Role",
            permissions=self.permission,
        )
        self.attach_role_facility_organization_user(
            user=self.user,
            facility_organization=self.facility_organization,
            role=self.role,
        )
        response = self.create_batch_request(requests=requests, user=self.user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        for result in response.data["results"]:
            self.assertEqual(result["status_code"], 200)
        encounter_data = next(
            (
                res
                for res in response.data["results"]
                if res["reference_id"] == "encounter_create"
            ),
            None,
        )
        self.assertIsNotNone(encounter_data)
        self.assertEqual(
            encounter_data["data"]["patient"]["id"], str(self.patient.external_id)
        )

    def test_questionnaire_batch_request_with_replacements(self):
        """
        Fetching the patient and creating the encounter then creating a  request with questionnaire submission along with
        structured data types like allergy and diagnosis with replacements.
        """
        patient_request = self.create_request(
            url=reverse("patient-detail", args=[self.patient.external_id]),
            method="GET",
            reference_id="patient_fetch",
        )
        encounter_request = self.create_request(
            url=reverse("encounter-list"),
            method="POST",
            body={
                "patient": None,
                "facility": self.facility.external_id,
                "organizations": [str(self.facility_organization.external_id)],
                "encounter_class": "imp",
                "status": "planned",
                "priority": "routine",
            },
            reference_id="encounter_create",
            replacements=[
                {
                    "source_path": {"reference_id": "patient_fetch", "path": "id"},
                    "value_path": {
                        "reference_id": "encounter_create",
                        "path": "patient",
                    },
                }
            ],
        )
        questionnaire_requests = self.create_request(
            url="/api/v1/questionnaire/testquestionnaire/submit/",
            method="POST",
            reference_id="questionnaire_submit",
            body={
                "resource_id": None,
                "encounter": None,
                "patient": None,
                "results": [
                    {
                        "question_id": "889833b0-68a2-4f5a-bf54-619b93b3cb73",
                        "values": [{"value": "Test response"}],
                    }
                ],
            },
            replacements=[
                {
                    "source_path": {"reference_id": "encounter_create", "path": "id"},
                    "value_path": {
                        "reference_id": "questionnaire_submit",
                        "path": "resource_id",
                    },
                },
                {
                    "source_path": {"reference_id": "encounter_create", "path": "id"},
                    "value_path": {
                        "reference_id": "questionnaire_submit",
                        "path": "encounter",
                    },
                },
                {
                    "source_path": {"reference_id": "patient_fetch", "path": "id"},
                    "value_path": {
                        "reference_id": "questionnaire_submit",
                        "path": "patient",
                    },
                },
            ],
        )
        allergy_request = self.create_request(
            url="/api/v1/patient/{patient_id}/allergy_intolerance/upsert/",
            method="POST",
            body={
                "datapoints": [
                    {
                        "code": {
                            "code": "50020101000188103",
                            "display": "Benzenesulfonic acid",
                            "system": "http://snomed.info/sct",
                        },
                        "clinical_status": "active",
                        "verification_status": "confirmed",
                        "category": "medication",
                        "criticality": "low",
                        "encounter": None,
                    },
                    {
                        "code": {
                            "code": "842825221000119100",
                            "display": "Anifrolumab",
                            "system": "http://snomed.info/sct",
                        },
                        "clinical_status": "active",
                        "verification_status": "confirmed",
                        "category": "medication",
                        "criticality": "low",
                        "encounter": None,
                    },
                    {
                        "code": {
                            "code": "3577911000001100",
                            "display": "Purified water",
                            "system": "http://snomed.info/sct",
                        },
                        "clinical_status": "active",
                        "verification_status": "confirmed",
                        "category": "medication",
                        "criticality": "low",
                        "encounter": None,
                    },
                    {
                        "code": {
                            "code": "42544811000001108",
                            "display": "Fezolinetant",
                            "system": "http://snomed.info/sct",
                        },
                        "clinical_status": "active",
                        "verification_status": "confirmed",
                        "category": "medication",
                        "criticality": "low",
                        "encounter": None,
                    },
                ]
            },
            reference_id="allergy_intolerance",
            replacements=[
                {
                    "source_path": {"reference_id": "patient_fetch", "path": "id"},
                    "value_path": {
                        "reference_id": "allergy_intolerance",
                        "path": "patient_id",
                        "type": "url",
                    },
                },
                {
                    "source_path": {"reference_id": "encounter_create", "path": "id"},
                    "value_path": {
                        "reference_id": "allergy_intolerance",
                        "path": "datapoints[*].encounter",
                    },
                },
            ],
        )

        diagnosis_request = self.create_request(
            url="/api/v1/patient/{patient_id}/diagnosis/upsert/",
            method="POST",
            body={
                "datapoints": [
                    {
                        "code": {
                            "code": "972604701000119104",
                            "display": "Acquired arteriovenous malformation of vascular structure of gastrointestinal tract",
                            "system": "http://snomed.info/sct",
                        },
                        "clinical_status": "active",
                        "verification_status": "confirmed",
                        "severity": "moderate",
                        "category": "encounter_diagnosis",
                        "onset": {"onset_datetime": "2026-02-03"},
                        "encounter": None,
                    },
                    {
                        "code": {
                            "code": "969688801000119108",
                            "display": "Acute left-sided ulcerative colitis",
                            "system": "http://snomed.info/sct",
                        },
                        "clinical_status": "active",
                        "verification_status": "confirmed",
                        "severity": "moderate",
                        "category": "encounter_diagnosis",
                        "onset": {"onset_datetime": "2026-02-03"},
                        "encounter": None,
                    },
                    {
                        "code": {
                            "code": "971608291000119105",
                            "display": "Venous ulcer of left ankle",
                            "system": "http://snomed.info/sct",
                        },
                        "clinical_status": "active",
                        "verification_status": "confirmed",
                        "severity": "moderate",
                        "category": "encounter_diagnosis",
                        "onset": {"onset_datetime": "2026-02-03"},
                        "encounter": None,
                    },
                    {
                        "code": {
                            "code": "971918681000119107",
                            "display": "Chronic respiratory failure due to obstructive sleep apnoea",
                            "system": "http://snomed.info/sct",
                        },
                        "clinical_status": "active",
                        "verification_status": "confirmed",
                        "severity": "moderate",
                        "category": "encounter_diagnosis",
                        "onset": {"onset_datetime": "2026-02-03"},
                        "encounter": None,
                    },
                ]
            },
            reference_id="diagnosis",
            replacements=[
                {
                    "source_path": {"reference_id": "patient_fetch", "path": "id"},
                    "value_path": {
                        "reference_id": "diagnosis",
                        "path": "patient_id",
                        "type": "url",
                    },
                },
                {
                    "source_path": {"reference_id": "encounter_create", "path": "id"},
                    "value_path": {
                        "reference_id": "diagnosis",
                        "path": "datapoints[*].encounter",
                    },
                },
            ],
        )

        requests = [
            patient_request,
            encounter_request,
            questionnaire_requests,
            allergy_request,
            diagnosis_request,
        ]
        response = self.create_batch_request(requests=requests)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 5)
        refernce_ids = [req["reference_id"] for req in response.data["results"]]
        self.assertIn("patient_fetch", refernce_ids)
        self.assertIn("encounter_create", refernce_ids)
        self.assertIn("allergy_intolerance", refernce_ids)
        self.assertIn("diagnosis", refernce_ids)
        self.assertIn("questionnaire_submit", refernce_ids)
        for result in response.data["results"]:
            self.assertEqual(result["status_code"], 200)

    def test_questionnaire_batch_request_with_replacements_with_permission(self):
        """
        Fetching the patient and creating the encounter then creating a  request with questionnaire submission along with
        structured data types like allergy and diagnosis with replacements with proper permissions.
        """
        permissions = [
            PatientPermissions.can_view_clinical_data.name,
            PatientPermissions.can_write_patient.name,
            EncounterPermissions.can_create_encounter.name,
            EncounterPermissions.can_submit_encounter_questionnaire.name,
            EncounterPermissions.can_write_encounter_clinical_data.name,
            QuestionnairePermissions.can_read_questionnaire.name,
        ]
        role = self.create_role_with_permissions(
            role_name="Test Role", permissions=permissions
        )
        self.attach_role_facility_organization_user(
            user=self.user, facility_organization=self.facility_organization, role=role
        )
        self.attach_role_organization_user(
            user=self.user, organization=self.organization, role=role
        )
        patient_request = self.create_request(
            url=reverse("patient-detail", args=[self.patient.external_id]),
            method="GET",
            reference_id="patient_fetch",
        )
        encounter_request = self.create_request(
            url=reverse("encounter-list"),
            method="POST",
            body={
                "patient": None,
                "facility": self.facility.external_id,
                "organizations": [str(self.facility_organization.external_id)],
                "encounter_class": "imp",
                "status": "planned",
                "priority": "routine",
            },
            reference_id="encounter_create",
            replacements=[
                {
                    "source_path": {"reference_id": "patient_fetch", "path": "id"},
                    "value_path": {
                        "reference_id": "encounter_create",
                        "path": "patient",
                    },
                }
            ],
        )
        questionnaire_requests = self.create_request(
            url="/api/v1/questionnaire/testquestionnaire/submit/",
            method="POST",
            reference_id="questionnaire_submit",
            body={
                "resource_id": None,
                "encounter": None,
                "patient": None,
                "results": [
                    {
                        "question_id": "889833b0-68a2-4f5a-bf54-619b93b3cb73",
                        "values": [{"value": "Test response"}],
                    }
                ],
            },
            replacements=[
                {
                    "source_path": {"reference_id": "encounter_create", "path": "id"},
                    "value_path": {
                        "reference_id": "questionnaire_submit",
                        "path": "resource_id",
                    },
                },
                {
                    "source_path": {"reference_id": "encounter_create", "path": "id"},
                    "value_path": {
                        "reference_id": "questionnaire_submit",
                        "path": "encounter",
                    },
                },
                {
                    "source_path": {"reference_id": "patient_fetch", "path": "id"},
                    "value_path": {
                        "reference_id": "questionnaire_submit",
                        "path": "patient",
                    },
                },
            ],
        )
        allergy_request = self.create_request(
            url="/api/v1/patient/{patient_id}/allergy_intolerance/upsert/",
            method="POST",
            body={
                "datapoints": [
                    {
                        "code": {
                            "code": "50020101000188103",
                            "display": "Benzenesulfonic acid",
                            "system": "http://snomed.info/sct",
                        },
                        "clinical_status": "active",
                        "verification_status": "confirmed",
                        "category": "medication",
                        "criticality": "low",
                        "encounter": None,
                    },
                    {
                        "code": {
                            "code": "842825221000119100",
                            "display": "Anifrolumab",
                            "system": "http://snomed.info/sct",
                        },
                        "clinical_status": "active",
                        "verification_status": "confirmed",
                        "category": "medication",
                        "criticality": "low",
                        "encounter": None,
                    },
                    {
                        "code": {
                            "code": "3577911000001100",
                            "display": "Purified water",
                            "system": "http://snomed.info/sct",
                        },
                        "clinical_status": "active",
                        "verification_status": "confirmed",
                        "category": "medication",
                        "criticality": "low",
                        "encounter": None,
                    },
                    {
                        "code": {
                            "code": "42544811000001108",
                            "display": "Fezolinetant",
                            "system": "http://snomed.info/sct",
                        },
                        "clinical_status": "active",
                        "verification_status": "confirmed",
                        "category": "medication",
                        "criticality": "low",
                        "encounter": None,
                    },
                ]
            },
            reference_id="allergy_intolerance",
            replacements=[
                {
                    "source_path": {"reference_id": "patient_fetch", "path": "id"},
                    "value_path": {
                        "reference_id": "allergy_intolerance",
                        "path": "patient_id",
                        "type": "url",
                    },
                },
                {
                    "source_path": {"reference_id": "encounter_create", "path": "id"},
                    "value_path": {
                        "reference_id": "allergy_intolerance",
                        "path": "datapoints[*].encounter",
                    },
                },
            ],
        )

        diagnosis_request = self.create_request(
            url="/api/v1/patient/{patient_id}/diagnosis/upsert/",
            method="POST",
            body={
                "datapoints": [
                    {
                        "code": {
                            "code": "972604701000119104",
                            "display": "Acquired arteriovenous malformation of vascular structure of gastrointestinal tract",
                            "system": "http://snomed.info/sct",
                        },
                        "clinical_status": "active",
                        "verification_status": "confirmed",
                        "severity": "moderate",
                        "category": "encounter_diagnosis",
                        "onset": {"onset_datetime": "2026-02-03"},
                        "encounter": None,
                    },
                    {
                        "code": {
                            "code": "969688801000119108",
                            "display": "Acute left-sided ulcerative colitis",
                            "system": "http://snomed.info/sct",
                        },
                        "clinical_status": "active",
                        "verification_status": "confirmed",
                        "severity": "moderate",
                        "category": "encounter_diagnosis",
                        "onset": {"onset_datetime": "2026-02-03"},
                        "encounter": None,
                    },
                    {
                        "code": {
                            "code": "971608291000119105",
                            "display": "Venous ulcer of left ankle",
                            "system": "http://snomed.info/sct",
                        },
                        "clinical_status": "active",
                        "verification_status": "confirmed",
                        "severity": "moderate",
                        "category": "encounter_diagnosis",
                        "onset": {"onset_datetime": "2026-02-03"},
                        "encounter": None,
                    },
                    {
                        "code": {
                            "code": "971918681000119107",
                            "display": "Chronic respiratory failure due to obstructive sleep apnoea",
                            "system": "http://snomed.info/sct",
                        },
                        "clinical_status": "active",
                        "verification_status": "confirmed",
                        "severity": "moderate",
                        "category": "encounter_diagnosis",
                        "onset": {"onset_datetime": "2026-02-03"},
                        "encounter": None,
                    },
                ]
            },
            reference_id="diagnosis",
            replacements=[
                {
                    "source_path": {"reference_id": "patient_fetch", "path": "id"},
                    "value_path": {
                        "reference_id": "diagnosis",
                        "path": "patient_id",
                        "type": "url",
                    },
                },
                {
                    "source_path": {"reference_id": "encounter_create", "path": "id"},
                    "value_path": {
                        "reference_id": "diagnosis",
                        "path": "datapoints[*].encounter",
                    },
                },
            ],
        )

        requests = [
            patient_request,
            encounter_request,
            questionnaire_requests,
            allergy_request,
            diagnosis_request,
        ]
        response = self.create_batch_request(requests=requests, user=self.user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 5)
        refernce_ids = [req["reference_id"] for req in response.data["results"]]
        self.assertIn("patient_fetch", refernce_ids)
        self.assertIn("encounter_create", refernce_ids)
        self.assertIn("allergy_intolerance", refernce_ids)
        self.assertIn("diagnosis", refernce_ids)
        self.assertIn("questionnaire_submit", refernce_ids)
        for result in response.data["results"]:
            self.assertEqual(result["status_code"], 200)

    def test_batch_request_with_replacement_with_invalid_permission(self):
        """
        Test creating a batch request with replacement details on
        fetching the patient and create encounter for that patient
        with invalid permissions.
        """
        patient_request = self.create_request(
            url=reverse("patient-detail", args=[self.patient.external_id]),
            method="GET",
            reference_id="patient_fetch",
        )
        encounter_request = self.create_request(
            url=reverse("encounter-list"),
            method="POST",
            body={
                "patient": None,
                "facility": self.facility.external_id,
                "organizations": [str(self.facility_organization.external_id)],
                "encounter_class": "imp",
                "status": "planned",
                "priority": "routine",
            },
            reference_id="encounter_create",
            replacements=[
                {
                    "source_path": {"reference_id": "patient_fetch", "path": "id"},
                    "value_path": {
                        "reference_id": "encounter_create",
                        "path": "patient",
                    },
                }
            ],
        )
        questionnaire_requests = self.create_request(
            url="/api/v1/questionnaire/testquestionnaire/submit/",
            method="POST",
            reference_id="questionnaire_submit",
            body={
                "resource_id": None,
                "encounter": None,
                "patient": None,
                "results": [
                    {
                        "question_id": "889833b0-68a2-4f5a-bf54-619b93b3cb73",
                        "values": [{"value": "Test response"}],
                    }
                ],
            },
            replacements=[
                {
                    "source_path": {"reference_id": "encounter_create", "path": "id"},
                    "value_path": {
                        "reference_id": "questionnaire_submit",
                        "path": "resource_id",
                    },
                },
                {
                    "source_path": {"reference_id": "encounter_create", "path": "id"},
                    "value_path": {
                        "reference_id": "questionnaire_submit",
                        "path": "encounter",
                    },
                },
                {
                    "source_path": {"reference_id": "patient_fetch", "path": "id"},
                    "value_path": {
                        "reference_id": "questionnaire_submit",
                        "path": "patient",
                    },
                },
            ],
        )
        allergy_request = self.create_request(
            url="/api/v1/patient/{patient_id}/allergy_intolerance/upsert/",
            method="POST",
            body={
                "datapoints": [
                    {
                        "code": {
                            "code": "50020101000188103",
                            "display": "Benzenesulfonic acid",
                            "system": "http://snomed.info/sct",
                        },
                        "clinical_status": "active",
                        "verification_status": "confirmed",
                        "category": "medication",
                        "criticality": "low",
                        "encounter": None,
                    },
                    {
                        "code": {
                            "code": "842825221000119100",
                            "display": "Anifrolumab",
                            "system": "http://snomed.info/sct",
                        },
                        "clinical_status": "active",
                        "verification_status": "confirmed",
                        "category": "medication",
                        "criticality": "low",
                        "encounter": None,
                    },
                    {
                        "code": {
                            "code": "3577911000001100",
                            "display": "Purified water",
                            "system": "http://snomed.info/sct",
                        },
                        "clinical_status": "active",
                        "verification_status": "confirmed",
                        "category": "medication",
                        "criticality": "low",
                        "encounter": None,
                    },
                    {
                        "code": {
                            "code": "42544811000001108",
                            "display": "Fezolinetant",
                            "system": "http://snomed.info/sct",
                        },
                        "clinical_status": "active",
                        "verification_status": "confirmed",
                        "category": "medication",
                        "criticality": "low",
                        "encounter": None,
                    },
                ]
            },
            reference_id="allergy_intolerance",
            replacements=[
                {
                    "source_path": {"reference_id": "patient_fetch", "path": "id"},
                    "value_path": {
                        "reference_id": "allergy_intolerance",
                        "path": "patient_id",
                        "type": "url",
                    },
                },
                {
                    "source_path": {"reference_id": "encounter_create", "path": "id"},
                    "value_path": {
                        "reference_id": "allergy_intolerance",
                        "path": "datapoints[*].encounter",
                    },
                },
            ],
        )

        diagnosis_request = self.create_request(
            url="/api/v1/patient/{patient_id}/diagnosis/upsert/",
            method="POST",
            body={
                "datapoints": [
                    {
                        "code": {
                            "code": "972604701000119104",
                            "display": "Acquired arteriovenous malformation of vascular structure of gastrointestinal tract",
                            "system": "http://snomed.info/sct",
                        },
                        "clinical_status": "active",
                        "verification_status": "confirmed",
                        "severity": "moderate",
                        "category": "encounter_diagnosis",
                        "onset": {"onset_datetime": "2026-02-03"},
                        "encounter": None,
                    },
                    {
                        "code": {
                            "code": "969688801000119108",
                            "display": "Acute left-sided ulcerative colitis",
                            "system": "http://snomed.info/sct",
                        },
                        "clinical_status": "active",
                        "verification_status": "confirmed",
                        "severity": "moderate",
                        "category": "encounter_diagnosis",
                        "onset": {"onset_datetime": "2026-02-03"},
                        "encounter": None,
                    },
                    {
                        "code": {
                            "code": "971608291000119105",
                            "display": "Venous ulcer of left ankle",
                            "system": "http://snomed.info/sct",
                        },
                        "clinical_status": "active",
                        "verification_status": "confirmed",
                        "severity": "moderate",
                        "category": "encounter_diagnosis",
                        "onset": {"onset_datetime": "2026-02-03"},
                        "encounter": None,
                    },
                    {
                        "code": {
                            "code": "971918681000119107",
                            "display": "Chronic respiratory failure due to obstructive sleep apnoea",
                            "system": "http://snomed.info/sct",
                        },
                        "clinical_status": "active",
                        "verification_status": "confirmed",
                        "severity": "moderate",
                        "category": "encounter_diagnosis",
                        "onset": {"onset_datetime": "2026-02-03"},
                        "encounter": None,
                    },
                ]
            },
            reference_id="diagnosis",
            replacements=[
                {
                    "source_path": {"reference_id": "patient_fetch", "path": "id"},
                    "value_path": {
                        "reference_id": "diagnosis",
                        "path": "patient_id",
                        "type": "url",
                    },
                },
                {
                    "source_path": {"reference_id": "encounter_create", "path": "id"},
                    "value_path": {
                        "reference_id": "diagnosis",
                        "path": "datapoints[*].encounter",
                    },
                },
            ],
        )

        requests = [
            patient_request,
            encounter_request,
            questionnaire_requests,
            allergy_request,
            diagnosis_request,
        ]
        response = self.create_batch_request(requests=requests, user=self.user)
        self.assertEqual(response.status_code, 400)

    def test_batch_request_with_replacement_with_invalid_source_path_reference_id(self):
        """
        Test creating a batch request with replacement details where the source reference id in replacements is invalid.
        """
        patient_request = self.create_request(
            url=reverse("patient-detail", args=[self.patient.external_id]),
            method="GET",
            reference_id="patient_fetch",
        )
        encounter_request = self.create_request(
            url=reverse("encounter-list"),
            method="POST",
            body={
                "patient": None,
                "facility": self.facility.external_id,
                "organizations": [str(self.facility_organization.external_id)],
                "encounter_class": "imp",
                "status": "planned",
                "priority": "routine",
            },
            reference_id="encounter_create",
            replacements=[
                {
                    "source_path": {
                        "reference_id": "invalid_reference_id",
                        "path": "id",
                    },
                    "value_path": {
                        "reference_id": "encounter_create",
                        "path": "patient",
                    },
                }
            ],
        )

        requests = [patient_request, encounter_request]
        response = self.create_batch_request(requests=requests, user=self.user)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "Invalid source_path reference_id : invalid_reference_id",
        )

    def test_batch_request_with_replacement_with_invalid_value_path_reference_id(self):
        """
        Test creating a batch request with replacement details where the value_path reference id in replacements is invalid.
        """
        patient_request = self.create_request(
            url=reverse("patient-detail", args=[self.patient.external_id]),
            method="GET",
            reference_id="patient_fetch",
        )
        encounter_request = self.create_request(
            url=reverse("encounter-list"),
            method="POST",
            body={
                "patient": None,
                "facility": self.facility.external_id,
                "organizations": [str(self.facility_organization.external_id)],
                "encounter_class": "imp",
                "status": "planned",
                "priority": "routine",
            },
            reference_id="encounter_create",
            replacements=[
                {
                    "source_path": {"reference_id": "patient_fetch", "path": "id"},
                    "value_path": {
                        "reference_id": "invalid_reference_id",
                        "path": "patient",
                    },
                }
            ],
        )
        requests = [patient_request, encounter_request]
        response = self.create_batch_request(requests=requests, user=self.user)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "Invalid value_path reference_id : invalid_reference_id",
        )

    def test_batch_request_with_improperly_ordered_replacements(self):
        """
        Test creating a batch request with replacement details where the source request comes after the current request.
        """
        encounter_request = self.create_request(
            url=reverse("encounter-list"),
            method="POST",
            body={
                "patient": None,
                "facility": self.facility.external_id,
                "organizations": [str(self.facility_organization.external_id)],
                "encounter_class": "imp",
                "status": "planned",
                "priority": "routine",
            },
            reference_id="encounter_create",
            replacements=[
                {
                    "source_path": {"reference_id": "patient_fetch", "path": "id"},
                    "value_path": {
                        "reference_id": "encounter_create",
                        "path": "patient",
                    },
                }
            ],
        )
        patient_request = self.create_request(
            url=reverse("patient-detail", args=[self.patient.external_id]),
            method="GET",
            reference_id="patient_fetch",
        )
        requests = [encounter_request, patient_request]
        response = self.create_batch_request(requests=requests, user=self.user)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "Source request must come before the current request.",
        )

    def test_batch_request_with_replacement_with_invalid_destination_path(self):
        """
        Test creating a batch request with replacement details where the value path in replacements is invalid.
        """
        patient_request = self.create_request(
            url=reverse("patient-detail", args=[self.patient.external_id]),
            method="GET",
            reference_id="patient_fetch",
        )
        encounter_request = self.create_request(
            url=reverse("encounter-list"),
            method="POST",
            body={
                "patient": None,
                "facility": self.facility.external_id,
                "organizations": [str(self.facility_organization.external_id)],
                "encounter_class": "imp",
                "status": "planned",
                "priority": "routine",
            },
            reference_id="encounter_create",
            replacements=[
                {
                    "source_path": {"reference_id": "patient_fetch", "path": "id"},
                    "value_path": {
                        "reference_id": "encounter_create",
                        "path": "patients",
                    },
                }
            ],
        )

        requests = [patient_request, encounter_request]
        response = self.create_batch_request(requests=requests)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["detail"],
            "Invalid destination_path 'patients' for request encounter_create",
        )

    def test_batch_request_with_replacement_with_invalid_source_path(self):
        """
        Test creating a batch request with replacement details where the source path in replacements is invalid.
        """
        encounter_request = self.create_request(
            url=reverse("encounter-list"),
            method="POST",
            body={
                "patient": None,
                "facility": self.facility.external_id,
                "organizations": [str(self.facility_organization.external_id)],
                "encounter_class": "imp",
                "status": "planned",
                "priority": "routine",
            },
            reference_id="encounter_create",
            replacements=[
                {
                    "source_path": {
                        "reference_id": "invalid_reference_id",
                        "path": "id",
                    },
                    "value_path": {
                        "reference_id": "encounter_create",
                        "path": "patient",
                    },
                }
            ],
        )
        requests = [encounter_request]
        response = self.create_batch_request(requests=requests)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "Invalid source_path reference_id : invalid_reference_id",
        )

    def test_batch_request_with_replacement_with_invalid_url_path(self):
        """
        Test creating a batch request with replacement details where the url path in replacements is not present in url.
        """
        encounter_request = self.create_request(
            url=reverse("encounter-list"),
            method="POST",
            body={
                "patient": None,
                "facility": self.facility.external_id,
                "organizations": [str(self.facility_organization.external_id)],
                "encounter_class": "imp",
                "status": "planned",
                "priority": "routine",
            },
            reference_id="encounter_create",
            replacements=[
                {
                    "source_path": {"reference_id": "patient_fetch", "path": "id"},
                    "value_path": {
                        "reference_id": "encounter_create",
                        "path": "patient_id",
                        "type": "url",
                    },
                }
            ],
        )
        patient_request = self.create_request(
            url=reverse("patient-detail", args=[self.patient.external_id]),
            method="GET",
            reference_id="patient_fetch",
        )
        requests = [patient_request, encounter_request]
        response = self.create_batch_request(requests=requests)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["detail"],
            "URL path 'patient_id' not found in url for request encounter_create",
        )

    def test_batch_request_with_multiple_value_replacements_for_url(self):
        """
        Test creating a batch request with replacement details where multiple replacements have same source reference id.
        """
        patient_request = self.create_request(
            url=reverse("patient-detail", args=[self.patient.external_id]),
            method="GET",
            reference_id="patient_fetch",
        )
        encounter_request = self.create_request(
            url=reverse("encounter-list"),
            method="POST",
            body={
                "patient": None,
                "facility": self.facility.external_id,
                "organizations": [str(self.facility_organization.external_id)],
                "encounter_class": "imp",
                "status": "planned",
                "priority": "routine",
            },
            reference_id="encounter_create",
            replacements=[
                {
                    "source_path": {"reference_id": "patient_fetch", "path": "id"},
                    "value_path": {
                        "reference_id": "encounter_create",
                        "path": "patient",
                    },
                }
            ],
        )
        questionnaire_requests = self.create_request(
            url="/api/v1/questionnaire/testquestionnaire/submit/",
            method="POST",
            reference_id="questionnaire_submit",
            body={
                "resource_id": None,
                "encounter": None,
                "patient": None,
                "results": [
                    {
                        "question_id": "889833b0-68a2-4f5a-bf54-619b93b3cb73",
                        "values": [{"value": "Test response"}],
                    }
                ],
            },
            replacements=[
                {
                    "source_path": {"reference_id": "encounter_create", "path": "id"},
                    "value_path": {
                        "reference_id": "questionnaire_submit",
                        "path": "resource_id",
                    },
                },
                {
                    "source_path": {"reference_id": "encounter_create", "path": "id"},
                    "value_path": {
                        "reference_id": "questionnaire_submit",
                        "path": "encounter",
                    },
                },
                {
                    "source_path": {"reference_id": "patient_fetch", "path": "id"},
                    "value_path": {
                        "reference_id": "questionnaire_submit",
                        "path": "patient",
                    },
                },
            ],
        )
        questionnaire_response = self.create_request(
            url="/api/v1/patient/{patient_id}/questionnaire_response/?encounter={encounter_id}&subject_type=encounter",
            method="GET",
            reference_id="questionnaire_response_fetch",
            replacements=[
                {
                    "source_path": {"reference_id": "patient_fetch", "path": "id"},
                    "value_path": {
                        "reference_id": "questionnaire_response_fetch",
                        "path": "patient_id",
                        "type": "url",
                    },
                },
                {
                    "source_path": {"reference_id": "encounter_create", "path": "id"},
                    "value_path": {
                        "reference_id": "questionnaire_response_fetch",
                        "path": "encounter_id",
                        "type": "url",
                    },
                },
            ],
        )
        requests = [
            patient_request,
            encounter_request,
            questionnaire_requests,
            questionnaire_response,
        ]
        response = self.create_batch_request(requests=requests)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 4)
