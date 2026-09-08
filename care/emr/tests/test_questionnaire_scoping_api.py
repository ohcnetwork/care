import uuid

from django.urls import reverse

from care.emr.models import Questionnaire
from care.security.permissions.questionnaire import QuestionnairePermissions
from care.utils.tests.base import CareAPITestBase


def questionnaire_definition(slug, **overrides):
    """Minimal valid questionnaire create payload."""
    definition = {
        "title": f"Questionnaire {slug}",
        "slug": slug,
        "version": "1.0",
        "description": "Questionnaire scoping test",
        "status": "active",
        "subject_type": "encounter",
        "auth_context": "instance",
        "questions": [
            {
                "id": str(uuid.uuid4()),
                "link_id": "1",
                "type": "string",
                "text": "Note",
            }
        ],
    }
    definition.update(overrides)
    return definition


class QuestionnaireScopingTestBase(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.super_user = self.create_super_user()
        self.organization = self.create_organization(org_type="govt")
        self.facility = self.create_facility(self.super_user)
        self.facility_organization = self.create_facility_organization(self.facility)
        self.base_url = reverse("questionnaire-list")
        self.client.force_authenticate(user=self.super_user)

    def create_questionnaire(self, slug, **overrides):
        response = self.client.post(
            self.base_url, questionnaire_definition(slug, **overrides), format="json"
        )
        self.assertEqual(
            response.status_code,
            200,
            f"Questionnaire creation failed: {response.json()}",
        )
        return response.json()

    def create_facility_questionnaire(self, slug, facility=None, **overrides):
        facility = facility or self.facility
        return self.create_questionnaire(
            slug,
            auth_context="facility",
            facility=str(facility.external_id),
            **overrides,
        )

    def detail_url(self, questionnaire_id):
        return reverse(
            "questionnaire-detail", kwargs={"external_id": questionnaire_id}
        )

    def list_slugs(self, params=None):
        response = self.client.get(self.base_url, params or {})
        self.assertEqual(response.status_code, 200)
        return {entry["slug"] for entry in response.json()["results"]}


class QuestionnaireAuthContextCreateTests(QuestionnaireScopingTestBase):
    """Validation of the auth_context / facility / subject_type create rules."""

    def test_create_requires_auth_context(self):
        definition = questionnaire_definition("missing-auth-context")
        del definition["auth_context"]
        response = self.client.post(self.base_url, definition, format="json")
        self.assertEqual(response.status_code, 400)
        errors = response.json()["errors"]
        self.assertTrue(
            any(error["loc"] == ["auth_context"] for error in errors),
            f"Expected a missing auth_context error, got {errors}",
        )

    def test_facility_context_requires_facility(self):
        response = self.client.post(
            self.base_url,
            questionnaire_definition("facility-no-facility", auth_context="facility"),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Facility is required", str(response.json()["errors"]))

    def test_user_context_requires_facility(self):
        response = self.client.post(
            self.base_url,
            questionnaire_definition("user-no-facility", auth_context="user"),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Facility is required", str(response.json()["errors"]))

    def test_facility_organization_context_requires_facility_organization(self):
        response = self.client.post(
            self.base_url,
            questionnaire_definition(
                "org-no-org", auth_context="facility_organization"
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Facility organization is required", str(response.json()["errors"])
        )

    def test_patient_subject_type_rejected_outside_instance(self):
        response = self.client.post(
            self.base_url,
            questionnaire_definition(
                "facility-patient-subject",
                auth_context="facility",
                facility=str(self.facility.external_id),
                subject_type="patient",
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Patient questionnaires are only supported at the instance level",
            str(response.json()["errors"]),
        )

    def test_patient_subject_type_allowed_at_instance(self):
        questionnaire = self.create_questionnaire(
            "instance-patient-subject", subject_type="patient"
        )
        self.assertEqual(questionnaire["subject_type"], "patient")

    def test_facility_create_persists_facility_scope(self):
        questionnaire = self.create_facility_questionnaire("facility-scoped")
        obj = Questionnaire.objects.get(external_id=questionnaire["id"])
        self.assertEqual(obj.auth_context, "facility")
        self.assertEqual(obj.facility.external_id, self.facility.external_id)

    def test_update_ignores_auth_context_and_subject_type(self):
        questionnaire = self.create_facility_questionnaire("immutable-scope")
        payload = questionnaire_definition(
            "immutable-scope",
            auth_context="instance",
            subject_type="patient",
            questions=questionnaire["questions"],
        )
        response = self.client.put(
            self.detail_url(questionnaire["id"]), payload, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["subject_type"], "encounter")
        obj = Questionnaire.objects.get(external_id=questionnaire["id"])
        self.assertEqual(obj.auth_context, "facility")
        self.assertEqual(obj.subject_type, "encounter")
        self.assertEqual(obj.facility.external_id, self.facility.external_id)


class QuestionnaireVisibilityTests(QuestionnaireScopingTestBase):
    """Scoped queryset behaviour for facility and user questionnaires."""

    def setUp(self):
        super().setUp()
        self.reader = self.create_user()
        read_role = self.create_role_with_permissions(
            [QuestionnairePermissions.can_read_questionnaire.name]
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.reader, read_role
        )

    def set_facility_organizations(self, questionnaire_id, organizations):
        url = reverse(
            "questionnaire-set-facility-organizations",
            kwargs={"external_id": questionnaire_id},
        )
        response = self.client.post(
            url,
            {"facility_organizations": [str(o.external_id) for o in organizations]},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

    def test_facility_questionnaire_visible_to_facility_org_member(self):
        questionnaire = self.create_facility_questionnaire("facility-visible")
        self.set_facility_organizations(
            questionnaire["id"], [self.facility_organization]
        )

        self.client.force_authenticate(user=self.reader)
        self.assertIn("facility-visible", self.list_slugs())
        response = self.client.get(self.detail_url(questionnaire["id"]))
        self.assertEqual(response.status_code, 200)

    def test_facility_questionnaire_hidden_without_organization_tagging(self):
        questionnaire = self.create_facility_questionnaire("facility-untagged")

        self.client.force_authenticate(user=self.reader)
        self.assertNotIn("facility-untagged", self.list_slugs())
        response = self.client.get(self.detail_url(questionnaire["id"]))
        self.assertEqual(response.status_code, 404)

    def test_facility_questionnaire_hidden_from_other_facility_members(self):
        questionnaire = self.create_facility_questionnaire("facility-private")
        self.set_facility_organizations(
            questionnaire["id"], [self.facility_organization]
        )

        other_facility = self.create_facility(self.super_user)
        other_org = self.create_facility_organization(other_facility)
        outsider = self.create_user()
        read_role = self.create_role_with_permissions(
            [QuestionnairePermissions.can_read_questionnaire.name]
        )
        self.attach_role_facility_organization_user(other_org, outsider, read_role)

        self.client.force_authenticate(user=outsider)
        self.assertNotIn("facility-private", self.list_slugs())
        response = self.client.get(self.detail_url(questionnaire["id"]))
        self.assertEqual(response.status_code, 404)

    def test_user_questionnaire_visible_only_to_creator(self):
        author = self.create_user()
        write_role = self.create_role_with_permissions(
            [QuestionnairePermissions.can_write_questionnaire.name]
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, author, write_role
        )

        self.client.force_authenticate(user=author)
        response = self.client.post(
            self.base_url,
            questionnaire_definition(
                "user-private",
                auth_context="user",
                facility=str(self.facility.external_id),
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.json())
        questionnaire = response.json()

        self.assertIn("user-private", self.list_slugs())

        self.client.force_authenticate(user=self.reader)
        self.assertNotIn("user-private", self.list_slugs())
        response = self.client.get(self.detail_url(questionnaire["id"]))
        self.assertEqual(response.status_code, 404)


class QuestionnaireRevisionTests(QuestionnaireScopingTestBase):
    """Revision snapshots created by question edits."""

    def updated_payload(self, slug, questions):
        return questionnaire_definition(slug, questions=questions)

    def test_question_change_creates_revision_snapshot(self):
        questionnaire = self.create_questionnaire("versioned")
        self.assertEqual(questionnaire["internal_revision"], 1)

        questions = questionnaire["questions"]
        questions[0]["text"] = "Updated note"
        response = self.client.put(
            self.detail_url(questionnaire["id"]),
            self.updated_payload("versioned", questions),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.json())
        self.assertEqual(response.json()["internal_revision"], 2)

        head = Questionnaire.objects.get(external_id=questionnaire["id"])
        archived = Questionnaire.objects.get(latest_revision=head)
        self.assertEqual(archived.internal_revision, 1)
        self.assertEqual(archived.slug, "versioned")
        self.assertNotEqual(archived.external_id, head.external_id)

        # The archived revision is listed through the parent_revision filter
        listed = self.client.get(
            self.base_url, {"parent_revision": questionnaire["id"]}
        ).json()
        self.assertEqual(listed["count"], 1)
        self.assertEqual(listed["results"][0]["id"], str(archived.external_id))
        self.assertEqual(listed["results"][0]["internal_revision"], 1)

        # ... and hidden from the default listing
        self.assertNotIn(
            str(archived.external_id),
            {entry["id"] for entry in self.client.get(self.base_url).json()["results"]},
        )

    def test_metadata_only_update_does_not_create_revision(self):
        questionnaire = self.create_questionnaire("metadata-only")
        payload = self.updated_payload("metadata-only", questionnaire["questions"])
        payload["title"] = "Renamed questionnaire"
        response = self.client.put(
            self.detail_url(questionnaire["id"]), payload, format="json"
        )
        self.assertEqual(response.status_code, 200, response.json())
        self.assertEqual(response.json()["internal_revision"], 1)
        self.assertEqual(response.json()["title"], "Renamed questionnaire")
        head = Questionnaire.objects.get(external_id=questionnaire["id"])
        self.assertFalse(
            Questionnaire.objects.filter(latest_revision=head).exists()
        )

    def test_past_revision_cannot_be_updated(self):
        questionnaire = self.create_questionnaire("no-editing-history")
        questions = questionnaire["questions"]
        questions[0]["text"] = "Second revision"
        self.client.put(
            self.detail_url(questionnaire["id"]),
            self.updated_payload("no-editing-history", questions),
            format="json",
        )
        head = Questionnaire.objects.get(external_id=questionnaire["id"])
        archived = Questionnaire.objects.get(latest_revision=head)

        response = self.client.put(
            self.detail_url(str(archived.external_id)),
            self.updated_payload("no-editing-history", questions),
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("past revision", str(response.json()))


class QuestionnaireListFilterTests(QuestionnaireScopingTestBase):
    """auth_context and facility list filters."""

    def setUp(self):
        super().setUp()
        self.other_facility = self.create_facility(self.super_user)
        self.create_questionnaire("filter-instance")
        self.create_facility_questionnaire("filter-facility-a")
        self.create_facility_questionnaire(
            "filter-facility-b", facility=self.other_facility
        )

    def test_auth_context_filter(self):
        self.assertEqual(
            self.list_slugs({"auth_context": "facility"}),
            {"filter-facility-a", "filter-facility-b"},
        )
        self.assertEqual(
            self.list_slugs({"auth_context": "instance"}), {"filter-instance"}
        )

    def test_facility_filter(self):
        self.assertEqual(
            self.list_slugs({"facility": str(self.facility.external_id)}),
            {"filter-facility-a"},
        )

    def test_auth_context_and_facility_filters_combined(self):
        self.assertEqual(
            self.list_slugs(
                {
                    "auth_context": "facility",
                    "facility": str(self.other_facility.external_id),
                }
            ),
            {"filter-facility-b"},
        )


class QuestionnaireSlugScopingTests(QuestionnaireScopingTestBase):
    """Slug uniqueness is scoped per auth context."""

    def test_same_slug_in_different_auth_contexts_coexists(self):
        instance_questionnaire = self.create_questionnaire("shared-slug")
        facility_questionnaire = self.create_facility_questionnaire("shared-slug")

        self.assertNotEqual(
            instance_questionnaire["id"], facility_questionnaire["id"]
        )
        for questionnaire in (instance_questionnaire, facility_questionnaire):
            response = self.client.get(self.detail_url(questionnaire["id"]))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["slug"], "shared-slug")

    def test_same_slug_in_different_facilities_coexists(self):
        other_facility = self.create_facility(self.super_user)
        first = self.create_facility_questionnaire("shared-facility-slug")
        second = self.create_facility_questionnaire(
            "shared-facility-slug", facility=other_facility
        )
        self.assertNotEqual(first["id"], second["id"])
