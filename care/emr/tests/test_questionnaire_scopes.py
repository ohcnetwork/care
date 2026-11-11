from copy import deepcopy
from uuid import uuid4

from django.db import IntegrityError, transaction
from django.urls import reverse
from model_bakery import baker

from care.emr.models.questionnaire import Questionnaire, QuestionnaireResponse
from care.security.permissions.questionnaire import QuestionnairePermissions
from care.utils.tests.base import CareAPITestBase


class TestQuestionnaireScopes(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.admin = self.create_super_user()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.admin)
        self.other_facility = self.create_facility(user=self.admin)
        self.organization = self.create_facility_organization(
            facility=self.facility, parent=self.facility.default_internal_organization
        )
        self.patient = self.create_patient()
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )
        self.url = reverse("questionnaire-list")
        self.client.force_authenticate(self.admin)
        self.question = {
            "id": str(uuid4()),
            "link_id": "notes",
            "text": "Clinical notes",
            "type": "text",
        }

    def grant(self, user, organization, *permissions):
        role = self.create_role_with_permissions(list(permissions))
        self.attach_role_facility_organization_user(organization, user, role)

    def data(self, auth_context="instance", **kwargs):
        data = {
            "auth_context": auth_context,
            "slug": f"scope-{uuid4()}",
            "title": "Clinical questionnaire",
            "status": "active",
            "subject_type": "encounter",
            "questions": [deepcopy(self.question)],
        }
        if auth_context in ("user", "facility"):
            data["facility"] = str(self.facility.external_id)
        elif auth_context == "facility_organization":
            data["facility_organization"] = str(self.organization.external_id)
        return {**data, **kwargs}

    def create_questionnaire(self, auth_context="instance", **kwargs):
        response = self.client.post(
            self.url, self.data(auth_context, **kwargs), format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        return Questionnaire.objects.get(external_id=response.data["id"])

    def detail_url(self, questionnaire):
        return reverse(
            "questionnaire-detail", kwargs={"external_id": questionnaire.external_id}
        )

    def update_data(self, questionnaire, **kwargs):
        return {
            "slug": questionnaire.slug,
            "title": "Updated questionnaire",
            "status": "active",
            "questions": deepcopy(questionnaire.questions),
            **kwargs,
        }

    def submission_data(self, **kwargs):
        return {
            "patient": str(self.patient.external_id),
            "resource_id": str(self.patient.external_id),
            "encounter": str(self.encounter.external_id),
            "results": [
                {
                    "question_id": self.question["id"],
                    "values": [{"value": "Clinical note"}],
                }
            ],
            **kwargs,
        }

    def submit(self, questionnaire, **kwargs):
        return self.client.post(
            reverse(
                "questionnaire-submit",
                kwargs={"external_id": questionnaire.external_id},
            ),
            self.submission_data(**kwargs),
            format="json",
        )

    def test_create_all_auth_contexts_persists_scope_and_author(self):
        for context in ("instance", "facility", "facility_organization", "user"):
            with self.subTest(context=context):
                questionnaire = self.create_questionnaire(context)
                self.assertEqual(questionnaire.auth_context, context)
                self.assertEqual(questionnaire.created_by, self.admin)
                self.assertEqual(
                    questionnaire.facility,
                    None if context == "instance" else self.facility,
                )
                self.assertEqual(
                    questionnaire.facility_organization,
                    self.organization if context == "facility_organization" else None,
                )

    def test_patient_questionnaires_require_instance_context(self):
        for context in ("facility", "facility_organization", "user"):
            with self.subTest(context=context):
                response = self.client.post(
                    self.url, self.data(context, subject_type="patient"), format="json"
                )
                self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Questionnaire.objects.exists())

    def test_facility_and_organization_contexts_require_scope_identifiers(self):
        for context, field in (
            ("facility", "facility"),
            ("user", "facility"),
            ("facility_organization", "facility_organization"),
        ):
            with self.subTest(context=context):
                data = self.data(context)
                data.pop(field)
                response = self.client.post(self.url, data, format="json")
                self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Questionnaire.objects.exists())

    def test_only_superusers_can_create_instance_questionnaires(self):
        self.grant(
            self.user,
            self.facility.default_internal_organization,
            QuestionnairePermissions.can_write_questionnaire.name,
        )
        self.client.force_authenticate(self.user)
        response = self.client.post(self.url, self.data(), format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.assertFalse(Questionnaire.objects.exists())

    def test_facility_questionnaire_write_requires_facility_root_role(self):
        self.grant(
            self.user,
            self.organization,
            QuestionnairePermissions.can_write_questionnaire.name,
        )
        self.client.force_authenticate(self.user)
        response = self.client.post(self.url, self.data("facility"), format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.grant(
            self.user,
            self.facility.default_internal_organization,
            QuestionnairePermissions.can_write_questionnaire.name,
        )
        questionnaire = self.create_questionnaire("facility")
        response = self.client.put(
            self.detail_url(questionnaire),
            self.update_data(questionnaire),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        questionnaire.refresh_from_db()
        self.assertEqual(questionnaire.title, "Updated questionnaire")

    def test_organization_questionnaire_write_requires_matching_organization_role(self):
        self.grant(
            self.user,
            self.create_facility_organization(facility=self.facility),
            QuestionnairePermissions.can_write_questionnaire.name,
        )
        self.client.force_authenticate(self.user)
        response = self.client.post(
            self.url, self.data("facility_organization"), format="json"
        )
        self.assertEqual(response.status_code, 403, response.data)
        self.grant(
            self.user,
            self.organization,
            QuestionnairePermissions.can_write_questionnaire.name,
        )
        questionnaire = self.create_questionnaire("facility_organization")
        response = self.client.put(
            self.detail_url(questionnaire),
            self.update_data(questionnaire),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)

    def test_user_questionnaire_write_requires_creator_and_facility_permission(self):
        self.grant(
            self.user,
            self.organization,
            QuestionnairePermissions.can_write_questionnaire.name,
        )
        self.client.force_authenticate(self.user)
        questionnaire = self.create_questionnaire("user")
        other_user = self.create_user()
        self.grant(
            other_user,
            self.facility.default_internal_organization,
            QuestionnairePermissions.can_write_questionnaire.name,
        )
        self.client.force_authenticate(other_user)
        response = self.client.put(
            self.detail_url(questionnaire),
            self.update_data(questionnaire),
            format="json",
        )
        self.assertEqual(response.status_code, 403, response.data)
        questionnaire.refresh_from_db()
        self.assertEqual(questionnaire.title, "Clinical questionnaire")
        self.client.force_authenticate(self.user)
        response = self.client.put(
            self.detail_url(questionnaire),
            self.update_data(questionnaire),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)

    def test_scoped_retrieve_rejects_roles_from_another_facility(self):
        questionnaires = [
            self.create_questionnaire(context)
            for context in ("facility", "facility_organization", "user")
        ]
        self.grant(
            self.user,
            self.other_facility.default_internal_organization,
            QuestionnairePermissions.can_read_questionnaire.name,
        )
        self.client.force_authenticate(self.user)
        for questionnaire in questionnaires:
            with self.subTest(context=questionnaire.auth_context):
                self.assertEqual(
                    self.client.get(self.detail_url(questionnaire)).status_code, 403
                )

    def test_facility_list_includes_authorized_facility_and_excludes_others(self):
        own = self.create_questionnaire("facility")
        self.create_questionnaire(
            "facility", facility=str(self.other_facility.external_id)
        )
        self.create_questionnaire("instance")
        self.grant(
            self.user,
            self.facility.default_internal_organization,
            QuestionnairePermissions.can_read_questionnaire.name,
        )
        self.client.force_authenticate(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            [row["id"] for row in response.data["results"]], [str(own.external_id)]
        )

    def test_user_list_includes_own_questionnaires_without_read_role(self):
        self.grant(
            self.user,
            self.organization,
            QuestionnairePermissions.can_write_questionnaire.name,
        )
        self.client.force_authenticate(self.user)
        own = self.create_questionnaire("user")
        self.client.force_authenticate(self.admin)
        self.create_questionnaire("user")
        self.client.force_authenticate(self.user)
        response = self.client.get(self.url, {"auth_context": "user"})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            [row["id"] for row in response.data["results"]], [str(own.external_id)]
        )

    def test_organization_member_can_list_questionnaire_they_can_retrieve(self):
        questionnaire = self.create_questionnaire("facility_organization")
        self.grant(
            self.user,
            self.organization,
            QuestionnairePermissions.can_read_questionnaire.name,
        )
        self.client.force_authenticate(self.user)
        self.assertEqual(
            self.client.get(self.detail_url(questionnaire)).status_code, 200
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn(
            str(questionnaire.external_id),
            [row["id"] for row in response.data["results"]],
        )

    def test_organization_cache_sync_retains_owning_organization_and_ancestors(self):
        team = self.create_facility_organization(
            facility=self.facility, parent=self.organization
        )
        questionnaire = self.create_questionnaire(
            "facility_organization", facility_organization=str(team.external_id)
        )
        expected = {
            self.facility.default_internal_organization_id,
            self.organization.pk,
            team.pk,
        }
        self.assertEqual(set(questionnaire.internal_organization_cache), expected)
        for _ in range(2):
            questionnaire.sync_facility_org_cache()
            questionnaire.refresh_from_db()
            self.assertEqual(set(questionnaire.internal_organization_cache), expected)

    def test_ancestor_reader_can_list_child_organization_questionnaires_only(self):
        team = self.create_facility_organization(
            facility=self.facility, parent=self.organization
        )
        child_questionnaire = self.create_questionnaire(
            "facility_organization", facility_organization=str(team.external_id)
        )
        unrelated_organization = self.create_facility_organization(
            facility=self.facility, parent=self.facility.default_internal_organization
        )
        unrelated_questionnaire = self.create_questionnaire(
            "facility_organization",
            facility_organization=str(unrelated_organization.external_id),
        )
        self.grant(
            self.user,
            self.organization,
            QuestionnairePermissions.can_read_questionnaire.name,
        )
        self.client.force_authenticate(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            [row["id"] for row in response.data["results"]],
            [str(child_questionnaire.external_id)],
        )
        self.assertEqual(
            self.client.get(self.detail_url(child_questionnaire)).status_code, 200
        )
        self.assertEqual(
            self.client.get(self.detail_url(unrelated_questionnaire)).status_code, 403
        )

    def test_read_only_role_cannot_update_or_delete_scoped_questionnaire(self):
        questionnaire = self.create_questionnaire("facility")
        self.grant(
            self.user,
            self.facility.default_internal_organization,
            QuestionnairePermissions.can_read_questionnaire.name,
        )
        self.client.force_authenticate(self.user)
        self.assertEqual(
            self.client.get(self.detail_url(questionnaire)).status_code, 200
        )
        self.assertEqual(
            self.client.put(
                self.detail_url(questionnaire),
                self.update_data(questionnaire),
                format="json",
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.delete(self.detail_url(questionnaire)).status_code, 403
        )

    def test_creator_can_delete_user_questionnaire(self):
        self.grant(
            self.user,
            self.organization,
            QuestionnairePermissions.can_write_questionnaire.name,
        )
        self.client.force_authenticate(self.user)
        questionnaire = self.create_questionnaire("user")
        response = self.client.delete(self.detail_url(questionnaire))
        self.assertEqual(response.status_code, 204, response.data)
        self.assertFalse(Questionnaire.objects.filter(pk=questionnaire.pk).exists())

    def test_authorized_delete_hides_questionnaires_in_each_context(self):
        for context in ("instance", "facility", "facility_organization", "user"):
            with self.subTest(context=context):
                questionnaire = self.create_questionnaire(context)
                response = self.client.delete(self.detail_url(questionnaire))
                self.assertEqual(response.status_code, 204, response.data)
                self.assertEqual(
                    self.client.get(self.detail_url(questionnaire)).status_code, 404
                )

    def test_update_cannot_change_questionnaire_scope_or_creator(self):
        for context in ("instance", "facility", "facility_organization", "user"):
            with self.subTest(context=context):
                questionnaire = self.create_questionnaire(context)
                original_scope = (
                    questionnaire.auth_context,
                    questionnaire.facility_id,
                    questionnaire.facility_organization_id,
                    questionnaire.created_by_id,
                )
                response = self.client.put(
                    self.detail_url(questionnaire),
                    self.update_data(
                        questionnaire,
                        auth_context="user",
                        facility=str(self.other_facility.external_id),
                        facility_organization=str(self.organization.external_id),
                        created_by=str(self.user.external_id),
                    ),
                    format="json",
                )
                self.assertEqual(response.status_code, 200, response.data)
                questionnaire.refresh_from_db()
                self.assertEqual(
                    (
                        questionnaire.auth_context,
                        questionnaire.facility_id,
                        questionnaire.facility_organization_id,
                        questionnaire.created_by_id,
                    ),
                    original_scope,
                )

    def test_encounter_submission_requires_matching_questionnaire_facility(self):
        questionnaire = self.create_questionnaire(
            "facility", facility=str(self.other_facility.external_id)
        )
        response = self.submit(questionnaire)
        self.assertEqual(response.status_code, 403, response.data)
        self.assertFalse(QuestionnaireResponse.objects.exists())

    def test_scoped_questionnaires_can_be_submitted_to_own_facility_encounter(self):
        for context in ("user", "facility", "facility_organization"):
            with self.subTest(context=context):
                questionnaire = self.create_questionnaire(context)
                response = self.submit(questionnaire)
                self.assertEqual(response.status_code, 200, response.data)
                saved = QuestionnaireResponse.objects.get(
                    external_id=response.data["id"]
                )
                self.assertEqual(saved.questionnaire, questionnaire)
                self.assertEqual(saved.encounter, self.encounter)
                self.assertEqual(saved.patient, self.patient)
                self.assertEqual(saved.revision, questionnaire.internal_revision)

    def test_encounter_questionnaire_requires_encounter_for_same_patient(self):
        questionnaire = self.create_questionnaire()
        for data, expected_status in (
            ({"encounter": None}, 400),
            ({"patient": str(self.create_patient().external_id)}, 404),
        ):
            with self.subTest(data=data):
                response = self.submit(questionnaire, **data)
                self.assertEqual(response.status_code, expected_status, response.data)
        self.assertFalse(QuestionnaireResponse.objects.exists())

    def test_patient_questionnaire_rejects_an_encounter(self):
        questionnaire = self.create_questionnaire(subject_type="patient")
        response = self.submit(questionnaire)
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(QuestionnaireResponse.objects.exists())

    def test_question_changes_create_a_revision_preserving_scope(self):
        questionnaire = self.create_questionnaire("facility_organization")
        previous_questions = deepcopy(questionnaire.questions)
        new_questions = deepcopy(questionnaire.questions)
        new_questions[0]["text"] = "Revised clinical notes"
        response = self.client.put(
            self.detail_url(questionnaire),
            self.update_data(questionnaire, questions=new_questions),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        questionnaire.refresh_from_db()
        previous = Questionnaire.objects.get(latest_revision=questionnaire)
        self.assertEqual(questionnaire.internal_revision, 2)
        self.assertEqual(previous.internal_revision, 1)
        self.assertEqual(previous.questions, previous_questions)
        self.assertEqual(questionnaire.questions[0]["text"], "Revised clinical notes")
        for version in (questionnaire, previous):
            self.assertEqual(version.auth_context, "facility_organization")
            self.assertEqual(version.facility, self.facility)
            self.assertEqual(version.facility_organization, self.organization)
            self.assertEqual(version.created_by, self.admin)
        self.assertEqual(
            self.client.put(
                self.detail_url(previous), self.update_data(previous), format="json"
            ).status_code,
            403,
        )
        self.assertEqual(self.submit(previous).status_code, 400)

    def test_title_only_update_keeps_revision(self):
        questionnaire = self.create_questionnaire()
        response = self.client.put(
            self.detail_url(questionnaire),
            self.update_data(questionnaire),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        questionnaire.refresh_from_db()
        self.assertEqual(questionnaire.internal_revision, 1)
        self.assertFalse(
            Questionnaire.objects.filter(latest_revision=questionnaire).exists()
        )


class TestQuestionnaireSlugConstraints(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.other_user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.other_facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.other_organization = self.create_facility_organization(
            facility=self.facility
        )

    def make_questionnaire(self, context, **kwargs):
        return baker.make(
            Questionnaire,
            **{
                "slug": "shared-slug",
                "auth_context": context,
                "created_by": self.user,
                "facility": None if context == "instance" else self.facility,
                "facility_organization": self.organization
                if context == "facility_organization"
                else None,
                **kwargs,
            },
        )

    def test_duplicate_live_slug_is_rejected_within_each_scope(self):
        for context in ("instance", "facility", "facility_organization", "user"):
            with self.subTest(context=context):
                self.make_questionnaire(context)
                with self.assertRaises(IntegrityError), transaction.atomic():
                    self.make_questionnaire(context)

    def test_same_slug_can_be_reused_across_scope_boundaries(self):
        for context in ("instance", "facility", "facility_organization", "user"):
            self.make_questionnaire(context)
        self.make_questionnaire("facility", facility=self.other_facility)
        self.make_questionnaire(
            "facility_organization", facility_organization=self.other_organization
        )
        self.make_questionnaire("user", created_by=self.other_user)
        self.make_questionnaire("user", facility=self.other_facility)
        self.assertEqual(Questionnaire.objects.count(), 8)

    def test_deleted_and_historical_revisions_do_not_reserve_slugs(self):
        for context in ("instance", "facility", "facility_organization", "user"):
            with self.subTest(context=context):
                latest = self.make_questionnaire(context)
                self.make_questionnaire(context, latest_revision=latest)
                self.make_questionnaire(context, deleted=True)
        self.assertEqual(Questionnaire.objects.count(), 8)
