from model_bakery import baker

from care.emr.models.allergy_intolerance import AllergyIntolerance
from care.emr.models.condition import Condition
from care.security.permissions.encounter import EncounterPermissions
from care.security.permissions.patient import PatientPermissions
from care_mcp.tests.base import MCPTestBase, plugin_config


class ToolPermissionTests(MCPTestBase):
    """Tools must see exactly what Care's REST API would show the same user."""

    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.patient = self.create_patient()
        self.encounter = self.create_encounter(
            patient=self.patient, facility=self.facility, organization=self.organization
        )
        self.token = self.issue_token(self.user)

    def grant(self, *permissions):
        role = self.create_role_with_permissions([p.name for p in permissions])
        self.attach_role_facility_organization_user(self.organization, self.user, role)

    def test_get_current_user(self):
        data = self.tool_json("get_current_user", token=self.token)
        self.assertEqual(data["username"], self.user.username)

    def test_patient_hidden_without_access(self):
        result = self.call_tool(
            "get_patient", {"patient_id": str(self.patient.external_id)}, self.token
        )
        self.assertTrue(result["isError"])
        self.assertIn("404", result["content"][0]["text"])

    def test_patient_visible_with_access(self):
        self.grant(PatientPermissions.can_view_clinical_data)
        data = self.tool_json(
            "get_patient", {"patient_id": str(self.patient.external_id)}, self.token
        )
        self.assertEqual(data["id"], str(self.patient.external_id))

    def test_clinical_data_denied_without_access(self):
        result = self.call_tool(
            "list_allergies", {"patient_id": str(self.patient.external_id)}, self.token
        )
        self.assertTrue(result["isError"])
        self.assertIn("403", result["content"][0]["text"])
        self.assertIn("encounter_id", result["content"][0]["text"])

    def test_list_allergies(self):
        self.grant(PatientPermissions.can_view_clinical_data)
        baker.make(
            AllergyIntolerance,
            patient=self.patient,
            encounter=self.encounter,
            clinical_status="active",
            verification_status="confirmed",
        )
        baker.make(
            AllergyIntolerance,
            patient=self.patient,
            encounter=self.encounter,
            clinical_status="active",
            verification_status="entered_in_error",
        )
        data = self.tool_json(
            "list_allergies", {"patient_id": str(self.patient.external_id)}, self.token
        )
        self.assertEqual(data["count"], 1)

    def test_list_conditions_kinds(self):
        self.grant(PatientPermissions.can_view_clinical_data)
        for category in ("encounter_diagnosis", "problem_list_item"):
            baker.make(
                Condition,
                patient=self.patient,
                encounter=self.encounter,
                category=category,
                clinical_status="active",
                verification_status="confirmed",
            )
        args = {"patient_id": str(self.patient.external_id)}
        diagnoses = self.tool_json("list_conditions", args, self.token)
        symptoms = self.tool_json(
            "list_conditions", {**args, "kind": "symptom"}, self.token
        )
        self.assertEqual(diagnoses["count"], 1)
        self.assertEqual(diagnoses["results"][0]["category"], "encounter_diagnosis")
        self.assertEqual(symptoms["count"], 1)

    def test_list_encounters_for_facility(self):
        self.grant(EncounterPermissions.can_list_encounter)
        data = self.tool_json(
            "list_encounters",
            {"facility_id": str(self.facility.external_id), "active_only": True},
            self.token,
        )
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["id"], str(self.encounter.external_id))

    def test_list_encounters_requires_scope(self):
        result = self.call_tool("list_encounters", {}, self.token)
        self.assertTrue(result["isError"])

    def test_patient_summary(self):
        self.grant(
            PatientPermissions.can_view_clinical_data,
            PatientPermissions.can_list_patients,
        )
        data = self.tool_json(
            "get_patient_summary",
            {"patient_id": str(self.patient.external_id)},
            self.token,
        )
        self.assertEqual(data["patient"]["id"], str(self.patient.external_id))
        self.assertEqual(
            data["open_encounters"][0]["id"], str(self.encounter.external_id)
        )
        for section in (
            "open_encounters",
            "diagnoses",
            "symptoms",
            "allergies",
            "active_medications",
            "recent_observations",
        ):
            self.assertIsInstance(data[section], list, (section, data[section]))

    def test_patient_summary_reports_sections_it_cannot_read(self):
        self.grant(PatientPermissions.can_view_clinical_data)
        data = self.tool_json(
            "get_patient_summary",
            {"patient_id": str(self.patient.external_id)},
            self.token,
        )
        self.assertIn("403", data["open_encounters"]["error"])
        self.assertIsInstance(data["diagnoses"], list)

    def test_patient_summary_without_access(self):
        result = self.call_tool(
            "get_patient_summary",
            {"patient_id": str(self.patient.external_id)},
            self.token,
        )
        self.assertTrue(result["isError"])

    def test_list_api_endpoints(self):
        data = self.tool_json("list_api_endpoints", {"contains": "allergy"}, self.token)
        paths = [e["path"] for e in data["endpoints"]]
        self.assertIn(
            "/api/v1/patient/{patient_external_id}/allergy_intolerance/", paths
        )
        self.assertTrue(all(e["methods"] == ["GET"] for e in data["endpoints"]))
        auth = self.tool_json("list_api_endpoints", {"contains": "auth/"}, self.token)
        self.assertEqual(auth["count"], 0)

    def test_care_api_get(self):
        data = self.tool_json(
            "care_api_get", {"path": "users/getcurrentuser"}, self.token
        )
        self.assertEqual(data["username"], self.user.username)

    def test_care_api_get_blocks_sensitive_paths(self):
        for path in ("auth/login/", "/api/v1/mfa/", "../admin/", "users/?x=1"):
            result = self.call_tool("care_api_get", {"path": path}, self.token)
            self.assertTrue(result["isError"], path)

    def test_care_api_get_unknown_route(self):
        result = self.call_tool("care_api_get", {"path": "nope/"}, self.token)
        self.assertTrue(result["isError"])
        self.assertIn("404", result["content"][0]["text"])


class WriteToolTests(MCPTestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_super_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.patient = self.create_patient()
        self.encounter = self.create_encounter(
            patient=self.patient, facility=self.facility, organization=self.organization
        )
        self.token = self.issue_token(self.user, allow_writes=True)

    def test_create_through_care_api(self):
        with plugin_config(CARE_MCP_ALLOW_WRITES=True):
            data = self.tool_json(
                "care_api_request",
                {
                    "method": "POST",
                    "path": f"patient/{self.patient.external_id}/thread/",
                    "body": {
                        "title": "Plan for tomorrow",
                        "encounter": str(self.encounter.external_id),
                    },
                },
                self.token,
            )
        self.assertEqual(data["status_code"], 200)
        self.assertEqual(data["data"]["title"], "Plan for tomorrow")

    def test_failed_write_is_tool_error(self):
        with plugin_config(CARE_MCP_ALLOW_WRITES=True):
            result = self.call_tool(
                "care_api_request",
                {
                    "method": "POST",
                    "path": f"patient/{self.patient.external_id}/thread/",
                    "body": {},
                },
                self.token,
            )
        self.assertTrue(result["isError"])
