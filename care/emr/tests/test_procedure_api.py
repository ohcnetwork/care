import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

from django.urls import reverse
from model_bakery import baker

from care.emr.models import Procedure, ValueSet
from care.emr.models.questionnaire import QuestionnaireResponse
from care.emr.registries.care_valueset.care_valueset import validate_valueset
from care.emr.registries.system_questionnaire.system_questionnaire import (
    InternalQuestionnaireRegistry,
)
from care.emr.resources.encounter.constants import StatusChoices
from care.emr.resources.procedure.valueset import (
    CARE_PROCEDURE_CATEGORY_VALUESET,
    CARE_PROCEDURE_REASON_VALUESET,
    CARE_PROCEDURE_STATUS_REASON_VALUESET,
)
from care.security.permissions.encounter import EncounterPermissions
from care.security.permissions.patient import PatientPermissions
from care.utils.tests.base import CareAPITestBase
from care.utils.time_util import care_now


class TestProcedureViewSet(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.patient = self.create_patient()
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )
        self.client.force_authenticate(self.user)
        self.base_url = self.list_url(self.patient)
        self.code = {
            "system": "http://snomed.info/sct",
            "code": "80146002",
            "display": "Appendectomy",
        }

    def list_url(self, patient):
        return reverse(
            "procedure-list", kwargs={"patient_external_id": patient.external_id}
        )

    def detail_url(self, procedure, patient=None):
        return reverse(
            "procedure-detail",
            kwargs={
                "patient_external_id": (patient or self.patient).external_id,
                "external_id": procedure.external_id,
            },
        )

    def upsert_url(self, patient=None):
        return reverse(
            "procedure-upsert",
            kwargs={"patient_external_id": (patient or self.patient).external_id},
        )

    def grant_permissions(self, *permissions):
        role = self.create_role_with_permissions(list(permissions))
        self.attach_role_facility_organization_user(self.organization, self.user, role)

    def grant_clinical_access(self):
        self.grant_permissions(
            PatientPermissions.can_view_clinical_data.name,
            EncounterPermissions.can_read_encounter_clinical_data.name,
            EncounterPermissions.can_write_encounter_clinical_data.name,
        )

    def payload(self, **kwargs):
        return {
            "encounter": str(self.encounter.external_id),
            "status": "completed",
            "code": self.code,
            **kwargs,
        }

    def create_procedure(self, encounter=None, **kwargs):
        encounter = encounter or self.encounter
        return baker.make(
            Procedure,
            encounter=encounter,
            patient=encounter.patient,
            status="completed",
            code=self.code,
            **kwargs,
        )

    def create_other_encounter(self, patient=None):
        return self.create_encounter(
            patient=patient or self.patient,
            facility=self.facility,
            organization=self.create_facility_organization(facility=self.facility),
        )

    def enable_procedure_valueset_validation(self):
        for slug in [
            "system-procedure-code",
            CARE_PROCEDURE_STATUS_REASON_VALUESET.slug,
            CARE_PROCEDURE_CATEGORY_VALUESET.slug,
            CARE_PROCEDURE_REASON_VALUESET.slug,
        ]:
            ValueSet.objects.get_or_create(
                slug=slug,
                defaults={"name": slug, "status": "active", "compose": {"include": []}},
            )

        def lookup_code(valueset, coding):
            if coding.system != "http://snomed.info/sct":
                return False
            if valueset.slug == "system-procedure-code":
                return coding.code == self.code["code"]
            if valueset.slug == CARE_PROCEDURE_CATEGORY_VALUESET.slug:
                return coding.code in {"387713003", "103693007", "409063005"}
            if valueset.slug == CARE_PROCEDURE_REASON_VALUESET.slug:
                return coding.code in {"233604007", "44054006", self.code["code"]}
            return (
                valueset.slug == CARE_PROCEDURE_STATUS_REASON_VALUESET.slug
                and coding.code in {"416237000", "416406003"}
            )

        validator_patcher = patch(
            "care.emr.utils.valueset_coding_type.validate_valueset",
            side_effect=validate_valueset,
        )
        validator_patcher.start()
        self.addCleanup(validator_patcher.stop)
        lookup_patcher = patch.object(
            ValueSet, "lookup", autospec=True, side_effect=lookup_code
        )
        lookup = lookup_patcher.start()
        self.addCleanup(lookup_patcher.stop)
        return lookup

    def test_status_reason_accepts_valueset_codes_on_create_and_update(self):
        self.grant_clinical_access()
        lookup = self.enable_procedure_valueset_validation()
        reason = {
            "system": "http://snomed.info/sct",
            "code": "416237000",
            "display": "Procedure not done",
        }
        response = self.client.post(
            self.base_url, self.payload(status_reason=reason), format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        procedure = Procedure.objects.get(external_id=response.data["id"])
        self.assertEqual(procedure.status_reason, reason)

        reason = {
            "system": "http://snomed.info/sct",
            "code": "416406003",
            "display": "Procedure discontinued",
        }
        response = self.client.patch(
            self.detail_url(procedure), {"status_reason": reason}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        procedure.refresh_from_db()
        self.assertEqual(procedure.status_reason, reason)
        reason_lookups = [
            coding.code
            for (valueset, coding), _ in lookup.call_args_list
            if valueset.slug == CARE_PROCEDURE_STATUS_REASON_VALUESET.slug
        ]
        self.assertEqual(set(reason_lookups), {"416237000", "416406003"})

    def test_status_reason_rejects_procedure_codes_on_create(self):
        self.grant_clinical_access()
        self.enable_procedure_valueset_validation()
        response = self.client.post(
            self.base_url, self.payload(status_reason=self.code), format="json"
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("status_reason", response.data["errors"][0]["loc"])
        self.assertFalse(Procedure.objects.exists())
        self.assertFalse(QuestionnaireResponse.objects.exists())

    def test_status_reason_rejects_procedure_codes_on_update_without_mutation(self):
        self.grant_clinical_access()
        self.enable_procedure_valueset_validation()
        reason = {"system": "http://snomed.info/sct", "code": "416237000"}
        procedure = self.create_procedure(status_reason=reason, note="Original")
        response = self.client.patch(
            self.detail_url(procedure),
            {"status_reason": self.code, "note": "Changed"},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("status_reason", response.data["errors"][0]["loc"])
        procedure.refresh_from_db()
        self.assertEqual(procedure.status_reason, reason)
        self.assertEqual(procedure.note, "Original")
        self.assertFalse(QuestionnaireResponse.objects.exists())

    def test_status_reason_remains_optional_and_can_be_cleared(self):
        self.grant_clinical_access()
        lookup = self.enable_procedure_valueset_validation()
        response = self.client.post(self.base_url, self.payload(), format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIsNone(response.data["status_reason"])
        lookup.reset_mock()

        reason = {"system": "http://snomed.info/sct", "code": "416237000"}
        procedure = self.create_procedure(status_reason=reason)
        response = self.client.patch(
            self.detail_url(procedure), {"note": "Updated"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        procedure.refresh_from_db()
        self.assertEqual(procedure.status_reason, reason)
        response = self.client.patch(
            self.detail_url(procedure), {"status_reason": None}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        procedure.refresh_from_db()
        self.assertIsNone(procedure.status_reason)
        lookup.assert_not_called()

    def test_category_accepts_multiple_valueset_codes_on_create_and_update(self):
        self.grant_clinical_access()
        lookup = self.enable_procedure_valueset_validation()
        categories = [
            {
                "system": "http://snomed.info/sct",
                "code": "387713003",
                "display": "Surgical procedure",
            },
            {
                "system": "http://snomed.info/sct",
                "code": "103693007",
                "display": "Diagnostic procedure",
            },
        ]
        response = self.client.post(
            self.base_url, self.payload(category=categories), format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        procedure = Procedure.objects.get(external_id=response.data["id"])
        self.assertEqual(procedure.category, categories)

        categories = [
            {
                "system": "http://snomed.info/sct",
                "code": "409063005",
                "display": "Counselling",
            }
        ]
        response = self.client.patch(
            self.detail_url(procedure), {"category": categories}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        procedure.refresh_from_db()
        self.assertEqual(procedure.category, categories)
        category_lookups = {
            coding.code
            for (valueset, coding), _ in lookup.call_args_list
            if valueset.slug == CARE_PROCEDURE_CATEGORY_VALUESET.slug
        }
        self.assertEqual(category_lookups, {"387713003", "103693007", "409063005"})

    def test_category_rejects_mixed_valid_and_invalid_codes_on_create(self):
        self.grant_clinical_access()
        self.enable_procedure_valueset_validation()
        response = self.client.post(
            self.base_url,
            self.payload(
                category=[
                    {"system": "http://snomed.info/sct", "code": "387713003"},
                    self.code,
                ]
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("category", response.data["errors"][0]["loc"])
        self.assertFalse(Procedure.objects.exists())
        self.assertFalse(QuestionnaireResponse.objects.exists())

    def test_category_rejects_procedure_codes_on_update_without_mutation(self):
        self.grant_clinical_access()
        self.enable_procedure_valueset_validation()
        categories = [{"system": "http://snomed.info/sct", "code": "387713003"}]
        procedure = self.create_procedure(category=categories, note="Original")
        response = self.client.patch(
            self.detail_url(procedure),
            {"category": [self.code], "note": "Changed"},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("category", response.data["errors"][0]["loc"])
        procedure.refresh_from_db()
        self.assertEqual(procedure.category, categories)
        self.assertEqual(procedure.note, "Original")
        self.assertFalse(QuestionnaireResponse.objects.exists())

    def test_category_remains_optional_and_can_be_cleared(self):
        self.grant_clinical_access()
        lookup = self.enable_procedure_valueset_validation()
        response = self.client.post(self.base_url, self.payload(), format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["category"], [])
        lookup.reset_mock()

        categories = [{"system": "http://snomed.info/sct", "code": "387713003"}]
        procedure = self.create_procedure(category=categories)
        response = self.client.patch(
            self.detail_url(procedure), {"note": "Updated"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        procedure.refresh_from_db()
        self.assertEqual(procedure.category, categories)
        response = self.client.patch(
            self.detail_url(procedure), {"category": []}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        procedure.refresh_from_db()
        self.assertEqual(procedure.category, [])
        lookup.assert_not_called()

    def test_reason_accepts_clinical_findings_and_procedures_on_create_and_update(self):
        self.grant_clinical_access()
        lookup = self.enable_procedure_valueset_validation()
        reasons = [
            {
                "system": "http://snomed.info/sct",
                "code": "233604007",
                "display": "Pneumonia",
            },
            self.code,
        ]
        response = self.client.post(
            self.base_url, self.payload(reason=reasons), format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        procedure = Procedure.objects.get(external_id=response.data["id"])
        self.assertEqual(procedure.reason, reasons)

        reasons = [
            {
                "system": "http://snomed.info/sct",
                "code": "44054006",
                "display": "Type 2 diabetes mellitus",
            },
            self.code,
        ]
        response = self.client.patch(
            self.detail_url(procedure), {"reason": reasons}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        procedure.refresh_from_db()
        self.assertEqual(procedure.reason, reasons)
        reason_lookups = {
            coding.code
            for (valueset, coding), _ in lookup.call_args_list
            if valueset.slug == CARE_PROCEDURE_REASON_VALUESET.slug
        }
        self.assertEqual(reason_lookups, {"233604007", "44054006", self.code["code"]})

    def test_reason_rejects_mixed_valid_and_invalid_codes_on_create(self):
        self.grant_clinical_access()
        self.enable_procedure_valueset_validation()
        invalid_reasons = [
            {"system": "http://snomed.info/sct", "code": "invalid-reason"},
            {"system": "http://example.com/codes", "code": "233604007"},
        ]
        for invalid_reason in invalid_reasons:
            with self.subTest(reason=invalid_reason):
                response = self.client.post(
                    self.base_url,
                    self.payload(reason=[self.code, invalid_reason]),
                    format="json",
                )
                self.assertEqual(response.status_code, 400, response.data)
                self.assertIn("reason", response.data["errors"][0]["loc"])
        self.assertFalse(Procedure.objects.exists())
        self.assertFalse(QuestionnaireResponse.objects.exists())

    def test_reason_rejects_invalid_update_without_mutation(self):
        self.grant_clinical_access()
        self.enable_procedure_valueset_validation()
        reasons = [{"system": "http://snomed.info/sct", "code": "233604007"}]
        procedure = self.create_procedure(reason=reasons, note="Original")
        response = self.client.patch(
            self.detail_url(procedure),
            {
                "reason": [
                    self.code,
                    {"system": "http://snomed.info/sct", "code": "invalid-reason"},
                ],
                "note": "Changed",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("reason", response.data["errors"][0]["loc"])
        procedure.refresh_from_db()
        self.assertEqual(procedure.reason, reasons)
        self.assertEqual(procedure.note, "Original")
        self.assertFalse(QuestionnaireResponse.objects.exists())

    def test_reason_remains_optional_and_can_be_cleared(self):
        self.grant_clinical_access()
        lookup = self.enable_procedure_valueset_validation()
        response = self.client.post(self.base_url, self.payload(), format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["reason"], [])
        lookup.reset_mock()

        reasons = [{"system": "http://snomed.info/sct", "code": "233604007"}]
        procedure = self.create_procedure(reason=reasons)
        response = self.client.patch(
            self.detail_url(procedure), {"note": "Updated"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        procedure.refresh_from_db()
        self.assertEqual(procedure.reason, reasons)
        response = self.client.patch(
            self.detail_url(procedure), {"reason": []}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        procedure.refresh_from_db()
        self.assertEqual(procedure.reason, [])
        lookup.assert_not_called()

    def test_outcome_accepts_enum_values_on_create_and_update(self):
        self.grant_clinical_access()
        outcomes = ["successful", "unsuccessful", "partially_successful"]
        for index, outcome in enumerate(outcomes):
            with self.subTest(outcome=outcome):
                response = self.client.post(
                    self.base_url, self.payload(outcome=outcome), format="json"
                )
                self.assertEqual(response.status_code, 200, response.data)
                self.assertEqual(response.data["outcome"], outcome)
                procedure = Procedure.objects.get(external_id=response.data["id"])
                self.assertEqual(procedure.outcome, outcome)

                updated_outcome = outcomes[(index + 1) % len(outcomes)]
                response = self.client.patch(
                    self.detail_url(procedure),
                    {"outcome": updated_outcome},
                    format="json",
                )
                self.assertEqual(response.status_code, 200, response.data)
                self.assertEqual(response.data["outcome"], updated_outcome)
                procedure.refresh_from_db()
                self.assertEqual(procedure.outcome, updated_outcome)

    def test_outcome_rejects_invalid_values_and_coding_objects_on_create(self):
        self.grant_clinical_access()
        invalid_outcomes = [
            "success",
            "partially-successful",
            "partial_success",
            "",
            {
                "system": "http://snomed.info/sct",
                "code": "385669000",
                "display": "Successful",
            },
        ]
        for outcome in invalid_outcomes:
            with self.subTest(outcome=outcome):
                response = self.client.post(
                    self.base_url, self.payload(outcome=outcome), format="json"
                )
                self.assertEqual(response.status_code, 400, response.data)
                self.assertIn("outcome", response.data["errors"][0]["loc"])
        self.assertFalse(Procedure.objects.exists())
        self.assertFalse(QuestionnaireResponse.objects.exists())

    def test_outcome_rejects_invalid_updates_without_mutation(self):
        self.grant_clinical_access()
        procedure = self.create_procedure(outcome="successful", note="Original")
        invalid_outcomes = [
            "unknown",
            "partially-successful",
            {"system": "http://snomed.info/sct", "code": "385671000"},
        ]
        for outcome in invalid_outcomes:
            with self.subTest(outcome=outcome):
                response = self.client.patch(
                    self.detail_url(procedure),
                    {"outcome": outcome, "note": "Changed"},
                    format="json",
                )
                self.assertEqual(response.status_code, 400, response.data)
                self.assertIn("outcome", response.data["errors"][0]["loc"])
                procedure.refresh_from_db()
                self.assertEqual(procedure.outcome, "successful")
                self.assertEqual(procedure.note, "Original")
        self.assertFalse(QuestionnaireResponse.objects.exists())

    def test_outcome_remains_optional_and_can_be_cleared(self):
        self.grant_clinical_access()
        response = self.client.post(self.base_url, self.payload(), format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIsNone(response.data["outcome"])

        procedure = self.create_procedure(outcome="successful")
        response = self.client.patch(
            self.detail_url(procedure), {"note": "Updated"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["outcome"], "successful")
        procedure.refresh_from_db()
        self.assertEqual(procedure.outcome, "successful")

        response = self.client.patch(
            self.detail_url(procedure), {"outcome": None}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIsNone(response.data["outcome"])
        procedure.refresh_from_db()
        self.assertIsNone(procedure.outcome)

    def test_create_defaults_to_secondary_source_and_records_audit(self):
        self.grant_clinical_access()
        before = care_now()
        response = self.client.post(self.base_url, self.payload(), format="json")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(response.data["is_primary_source"])
        self.assertEqual(response.data["encounter"], str(self.encounter.external_id))
        procedure = Procedure.objects.get(external_id=response.data["id"])
        self.assertFalse(procedure.is_primary_source)
        self.assertEqual(procedure.patient, self.patient)
        self.assertEqual(procedure.created_by, self.user)
        self.assertEqual(procedure.updated_by, self.user)
        self.assertGreaterEqual(procedure.recorded_date, before)
        self.assertLessEqual(procedure.recorded_date, care_now())
        questionnaire_response = QuestionnaireResponse.objects.get(
            structured_response_type="procedure"
        )
        self.assertEqual(questionnaire_response.patient, self.patient)
        self.assertEqual(questionnaire_response.encounter, self.encounter)
        self.assertEqual(
            questionnaire_response.structured_responses,
            {"procedure": {"submit_type": "CREATE", "id": response.data["id"]}},
        )
        self.assertTrue(InternalQuestionnaireRegistry.check_type_exists("procedure"))

    def test_create_with_clinical_write_permission_without_patient_read(self):
        self.grant_permissions(
            EncounterPermissions.can_write_encounter_clinical_data.name
        )
        response = self.client.post(self.base_url, self.payload(), format="json")
        self.assertEqual(response.status_code, 200, response.data)

    def test_primary_source_is_server_owned_for_historical_records(self):
        self.grant_clinical_access()
        response = self.client.post(
            self.base_url, self.payload(is_primary_source=True), format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        procedure = Procedure.objects.get(external_id=response.data["id"])
        self.assertFalse(procedure.is_primary_source)

        response = self.client.patch(
            self.detail_url(procedure), {"is_primary_source": True}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        procedure.refresh_from_db()
        self.assertFalse(procedure.is_primary_source)
        self.assertEqual(procedure.code, self.code)
        self.assertEqual(procedure.status, "completed")

        # Existing primary-source provenance is retained when editing history.
        procedure.is_primary_source = True
        procedure.save(update_fields=["is_primary_source"])
        response = self.client.patch(
            self.detail_url(procedure), {"is_primary_source": False}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        procedure.refresh_from_db()
        self.assertTrue(procedure.is_primary_source)

    def test_partial_update_preserves_omitted_fields_and_clears_explicit_null(self):
        self.grant_clinical_access()
        procedure = self.create_procedure(note="Collected from an old record")
        response = self.client.patch(
            self.detail_url(procedure), {"note": None}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        procedure.refresh_from_db()
        self.assertIsNone(procedure.note)
        self.assertEqual(procedure.code, self.code)
        self.assertEqual(procedure.updated_by, self.user)
        self.assertEqual(
            QuestionnaireResponse.objects.get().structured_responses,
            {
                "procedure": {
                    "submit_type": "UPDATE",
                    "id": str(procedure.external_id),
                }
            },
        )

    def test_historical_occurrence_supports_date_period_and_approximate_text(self):
        self.grant_clinical_access()
        end = care_now() - timedelta(days=365)
        start = end - timedelta(days=1)
        occurrences = [
            {"occurrence_datetime": end.isoformat()},
            {"occurrence_period": {"start": start.isoformat(), "end": end.isoformat()}},
            {"occurrence_string": "During childhood"},
        ]
        for occurrence in occurrences:
            with self.subTest(occurrence=occurrence):
                response = self.client.post(
                    self.base_url, self.payload(occurrence=occurrence), format="json"
                )
                self.assertEqual(response.status_code, 200, response.data)
                procedure = Procedure.objects.get(external_id=response.data["id"])
                field, value = next(iter(occurrence.items()))
                if field == "occurrence_datetime":
                    self.assertEqual(
                        datetime.fromisoformat(procedure.occurrence[field]), end
                    )
                elif field == "occurrence_period":
                    for bound, expected in [("start", start), ("end", end)]:
                        self.assertEqual(
                            datetime.fromisoformat(procedure.occurrence[field][bound]),
                            expected,
                        )
                else:
                    self.assertEqual(procedure.occurrence[field], value)

    def test_rejects_future_or_ambiguous_occurrence(self):
        self.grant_clinical_access()
        future = care_now() + timedelta(days=1)
        past = care_now() - timedelta(days=1)
        occurrences = [
            {"occurrence_datetime": future.isoformat()},
            {"occurrence_period": {"start": future.isoformat()}},
            {"occurrence_period": {"end": future.isoformat()}},
            {
                "occurrence_period": {
                    "start": past.isoformat(),
                    "end": (past - timedelta(days=1)).isoformat(),
                }
            },
            {"occurrence_datetime": past.isoformat(), "occurrence_string": "Yesterday"},
            {"occurrence_string": "   "},
        ]
        for occurrence in occurrences:
            with self.subTest(occurrence=occurrence):
                response = self.client.post(
                    self.base_url, self.payload(occurrence=occurrence), format="json"
                )
                self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Procedure.objects.exists())

    def test_rejects_workflow_statuses(self):
        self.grant_clinical_access()
        for status in ["preparation", "in_progress", "on_hold", "planned"]:
            with self.subTest(status=status):
                response = self.client.post(
                    self.base_url, self.payload(status=status), format="json"
                )
                self.assertEqual(response.status_code, 400, response.data)

    def test_accepts_historical_statuses(self):
        self.grant_clinical_access()
        for status in [
            "completed",
            "not_done",
            "stopped",
            "entered_in_error",
            "unknown",
        ]:
            with self.subTest(status=status):
                response = self.client.post(
                    self.base_url, self.payload(status=status), format="json"
                )
                self.assertEqual(response.status_code, 200, response.data)
                self.assertEqual(response.data["status"], status)

    def test_demographic_permissions_do_not_allow_clinical_reads_or_writes(self):
        self.grant_permissions(
            PatientPermissions.can_write_patient.name,
            PatientPermissions.can_list_patients.name,
            EncounterPermissions.can_write_encounter.name,
            EncounterPermissions.can_read_encounter.name,
        )
        self.assertEqual(self.client.get(self.base_url).status_code, 403)
        response = self.client.post(self.base_url, self.payload(), format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.assertFalse(Procedure.objects.exists())

    def test_patient_clinical_read_permission_cannot_write(self):
        self.grant_permissions(PatientPermissions.can_view_clinical_data.name)
        procedure = self.create_procedure()
        self.assertEqual(self.client.get(self.detail_url(procedure)).status_code, 200)
        response = self.client.patch(
            self.detail_url(procedure), {"note": "Changed"}, format="json"
        )
        self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(
            self.client.delete(self.detail_url(procedure)).status_code, 403
        )

    def test_clinical_write_permission_allows_update_and_delete_without_read(self):
        self.grant_permissions(
            EncounterPermissions.can_write_encounter_clinical_data.name
        )
        procedure = self.create_procedure()
        for query in [{}, {"encounter": str(self.encounter.external_id)}]:
            with self.subTest(query=query):
                self.assertEqual(self.client.get(self.base_url, query).status_code, 403)
                self.assertEqual(
                    self.client.get(self.detail_url(procedure), query).status_code,
                    403,
                )

        response = self.client.patch(
            self.detail_url(procedure), {"note": "Updated"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        procedure.refresh_from_db()
        self.assertEqual(procedure.note, "Updated")
        response = self.client.delete(self.detail_url(procedure))
        self.assertEqual(response.status_code, 204, response.data)
        procedure.refresh_from_db()
        self.assertTrue(procedure.deleted)

    def test_clinical_write_permission_allows_upsert_update_without_read(self):
        self.grant_permissions(
            EncounterPermissions.can_write_encounter_clinical_data.name
        )
        procedure = self.create_procedure(note="Original")
        response = self.client.post(
            self.upsert_url(),
            {"datapoints": [{"id": str(procedure.external_id), "note": "Updated"}]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        procedure.refresh_from_db()
        self.assertEqual(procedure.note, "Updated")
        self.assertEqual(QuestionnaireResponse.objects.count(), 1)

    def test_clinical_write_permission_does_not_allow_other_encounter_writes(self):
        self.grant_permissions(
            EncounterPermissions.can_write_encounter_clinical_data.name
        )
        hidden = self.create_procedure(
            encounter=self.create_other_encounter(), note="Original"
        )
        response = self.client.patch(
            self.detail_url(hidden), {"note": "Changed"}, format="json"
        )
        self.assertEqual(response.status_code, 403, response.data)
        response = self.client.delete(self.detail_url(hidden))
        self.assertEqual(response.status_code, 403, response.data)
        response = self.client.post(
            self.upsert_url(),
            {"datapoints": [{"id": str(hidden.external_id), "note": "Changed"}]},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        hidden.refresh_from_db()
        self.assertEqual(hidden.note, "Original")
        self.assertFalse(hidden.deleted)
        self.assertFalse(QuestionnaireResponse.objects.exists())

    def test_write_only_requests_cannot_use_another_patients_url(self):
        self.grant_permissions(
            EncounterPermissions.can_write_encounter_clinical_data.name
        )
        procedure = self.create_procedure(note="Original")
        other_patient = self.create_patient()
        wrong_url = self.detail_url(procedure, patient=other_patient)
        response = self.client.patch(wrong_url, {"note": "Changed"}, format="json")
        self.assertEqual(response.status_code, 404, response.data)
        response = self.client.delete(wrong_url)
        self.assertEqual(response.status_code, 404, response.data)
        response = self.client.post(
            self.upsert_url(patient=other_patient),
            {"datapoints": [{"id": str(procedure.external_id), "note": "Changed"}]},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        procedure.refresh_from_db()
        self.assertEqual(procedure.note, "Original")
        self.assertFalse(procedure.deleted)
        self.assertFalse(QuestionnaireResponse.objects.exists())

    def test_patient_clinical_read_lists_history_across_encounters(self):
        self.grant_permissions(PatientPermissions.can_view_clinical_data.name)
        procedures = [
            self.create_procedure(),
            self.create_procedure(encounter=self.create_other_encounter()),
        ]
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertCountEqual(
            [item["id"] for item in response.data["results"]],
            [str(procedure.external_id) for procedure in procedures],
        )

    def test_encounter_only_reads_are_limited_to_the_authorized_encounter(self):
        self.grant_permissions(
            EncounterPermissions.can_read_encounter_clinical_data.name
        )
        visible = self.create_procedure()
        hidden = self.create_procedure(encounter=self.create_other_encounter())
        response = self.client.get(
            self.base_url, {"encounter": str(self.encounter.external_id)}
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [str(visible.external_id)],
        )
        self.assertEqual(
            self.client.get(
                self.detail_url(visible), {"encounter": self.encounter.external_id}
            ).status_code,
            200,
        )
        response = self.client.get(
            self.detail_url(hidden), {"encounter": self.encounter.external_id}
        )
        self.assertEqual(response.status_code, 404, response.data)
        self.assertEqual(self.client.get(self.base_url).status_code, 403)

    def test_retrieve_checks_the_objects_encounter_without_a_query_parameter(self):
        self.grant_permissions(
            EncounterPermissions.can_read_encounter_clinical_data.name
        )
        visible = self.create_procedure()
        hidden = self.create_procedure(encounter=self.create_other_encounter())
        response = self.client.get(self.detail_url(visible))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["id"], str(visible.external_id))
        response = self.client.get(self.detail_url(hidden))
        self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(self.client.get(self.base_url).status_code, 403)

    def test_encounter_read_cannot_authorize_another_patients_history(self):
        self.grant_permissions(
            EncounterPermissions.can_read_encounter_clinical_data.name
        )
        other_patient = self.create_patient()
        other_encounter = self.create_other_encounter(patient=other_patient)
        hidden = self.create_procedure(encounter=other_encounter)
        response = self.client.get(
            self.list_url(other_patient), {"encounter": self.encounter.external_id}
        )
        self.assertIn(response.status_code, [400, 403, 404], response.data)
        response = self.client.get(
            self.detail_url(hidden, patient=other_patient),
            {"encounter": self.encounter.external_id},
        )
        self.assertIn(response.status_code, [400, 403, 404], response.data)

    def test_cross_patient_create_and_detail_are_rejected(self):
        self.grant_clinical_access()
        other_patient = self.create_patient()
        response = self.client.post(
            self.list_url(other_patient), self.payload(), format="json"
        )
        self.assertIn(response.status_code, [400, 403, 404], response.data)
        self.assertFalse(Procedure.objects.exists())
        procedure = self.create_procedure()
        response = self.client.get(self.detail_url(procedure, patient=other_patient))
        self.assertIn(response.status_code, [403, 404], response.data)

    def test_invalid_encounter_is_rejected(self):
        self.grant_clinical_access()
        response = self.client.post(
            self.base_url,
            self.payload(encounter=str(uuid.uuid4())),
            format="json",
        )
        self.assertIn(response.status_code, [400, 404], response.data)
        self.assertFalse(Procedure.objects.exists())

    def test_recording_encounter_cannot_be_changed_by_update(self):
        self.grant_clinical_access()
        procedure = self.create_procedure()
        other_encounter = self.create_other_encounter(patient=self.create_patient())
        response = self.client.patch(
            self.detail_url(procedure),
            {"encounter": str(other_encounter.external_id), "note": "Updated"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        procedure.refresh_from_db()
        self.assertEqual(procedure.encounter, self.encounter)
        self.assertEqual(procedure.patient, self.patient)

    def test_closed_encounter_denies_create_update_and_delete(self):
        self.grant_clinical_access()
        procedure = self.create_procedure()
        self.encounter.status = StatusChoices.completed.value
        self.encounter.save(update_fields=["status"])
        encounter_query = f"?encounter={self.encounter.external_id}"
        response = self.client.post(self.base_url, self.payload(), format="json")
        self.assertEqual(response.status_code, 403, response.data)
        detail_url = self.detail_url(procedure) + encounter_query
        response = self.client.patch(detail_url, {"note": "Changed"}, format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(self.client.delete(detail_url).status_code, 403)
        procedure.refresh_from_db()
        self.assertFalse(procedure.deleted)
        self.assertIsNone(procedure.note)

    def test_delete_uses_clinical_write_permission_and_soft_deletes(self):
        self.grant_clinical_access()
        procedure = self.create_procedure()
        response = self.client.delete(self.detail_url(procedure))
        self.assertEqual(response.status_code, 204, response.data)
        self.assertFalse(Procedure.objects.filter(pk=procedure.pk).exists())
        procedure.refresh_from_db()
        self.assertTrue(procedure.deleted)

    def test_encounter_only_update_cannot_use_authorized_sibling_encounter(self):
        self.grant_permissions(
            EncounterPermissions.can_read_encounter_clinical_data.name,
            EncounterPermissions.can_write_encounter_clinical_data.name,
        )
        hidden = self.create_procedure(encounter=self.create_other_encounter())
        response = self.client.patch(
            f"{self.detail_url(hidden)}?encounter={self.encounter.external_id}",
            {"note": "Changed"},
            format="json",
        )
        self.assertEqual(response.status_code, 404, response.data)
        hidden.refresh_from_db()
        self.assertIsNone(hidden.note)

    def test_upsert_creates_and_updates_history(self):
        self.grant_clinical_access()
        procedure = self.create_procedure(note="Original")
        response = self.client.post(
            self.upsert_url(),
            {
                "datapoints": [
                    self.payload(),
                    {"id": str(procedure.external_id), "note": "Updated"},
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(Procedure.objects.count(), 2)
        procedure.refresh_from_db()
        self.assertEqual(procedure.note, "Updated")
        self.assertEqual(QuestionnaireResponse.objects.count(), 2)

    def test_upsert_rejects_cross_patient_updates_without_mutation(self):
        self.grant_clinical_access()
        other_patient = self.create_patient()
        other_encounter = self.create_encounter(
            patient=other_patient,
            facility=self.facility,
            organization=self.organization,
        )
        hidden = self.create_procedure(encounter=other_encounter, note="Original")
        response = self.client.post(
            self.upsert_url(),
            {"datapoints": [{"id": str(hidden.external_id), "note": "Changed"}]},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        hidden.refresh_from_db()
        self.assertEqual(hidden.note, "Original")
        self.assertFalse(QuestionnaireResponse.objects.exists())

    def test_upsert_cannot_bypass_encounter_scoping(self):
        self.grant_permissions(
            EncounterPermissions.can_read_encounter_clinical_data.name,
            EncounterPermissions.can_write_encounter_clinical_data.name,
        )
        hidden = self.create_procedure(encounter=self.create_other_encounter())
        response = self.client.post(
            f"{self.upsert_url()}?encounter={self.encounter.external_id}",
            {"datapoints": [{"id": str(hidden.external_id), "note": "Changed"}]},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        hidden.refresh_from_db()
        self.assertIsNone(hidden.note)

    def test_upsert_rolls_back_creations_and_audit_when_one_datapoint_is_invalid(self):
        self.grant_clinical_access()
        response = self.client.post(
            self.upsert_url(),
            {"datapoints": [self.payload(), self.payload(status="planned")]},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Procedure.objects.exists())
        self.assertFalse(QuestionnaireResponse.objects.exists())
