from uuid import uuid4

from django.urls import reverse
from model_bakery import baker

from care.emr.models.questionnaire import (
    Questionnaire,
    QuestionnaireFacilityOrganization,
)
from care.security.permissions.questionnaire import QuestionnairePermissions
from care.utils.tests.base import CareAPITestBase


class QuestionnaireFacilityOrganizationTests(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.admin = self.create_super_user()
        self.facility = self.create_facility(user=self.admin)
        self.root = self.facility.default_internal_organization
        self.department = self.create_facility_organization(
            facility=self.facility, parent=self.root, org_type="dept", name="Outpatient"
        )
        self.team = self.create_facility_organization(
            facility=self.facility,
            parent=self.department,
            org_type="team",
            name="Consultation",
        )
        self.other_department = self.create_facility_organization(
            facility=self.facility, parent=self.root, org_type="dept", name="Inpatient"
        )
        self.questionnaire = self.make_questionnaire()
        self.client.force_authenticate(self.admin)

    def make_questionnaire(self, **kwargs):
        questionnaire = baker.make(
            Questionnaire,
            **(
                {
                    "auth_context": "facility",
                    "facility": self.facility,
                    "subject_type": "encounter",
                    "status": "active",
                    "questions": [],
                    "created_by": self.admin,
                    "updated_by": self.admin,
                }
                | kwargs
            ),
        )
        questionnaire.sync_facility_org_cache()
        return questionnaire

    def url(self, action, questionnaire=None):
        return reverse(
            f"questionnaire-{action}-facility-organizations",
            kwargs={"external_id": (questionnaire or self.questionnaire).external_id},
        )

    def set_organizations(self, organizations, questionnaire=None):
        return self.client.post(
            self.url("set", questionnaire),
            {"facility_organizations": [str(org.external_id) for org in organizations]},
            format="json",
        )

    def assert_assignments(self, organization_ids, cache_ids):
        self.assertEqual(
            set(
                QuestionnaireFacilityOrganization.objects.filter(
                    questionnaire=self.questionnaire
                ).values_list("organization_id", flat=True)
            ),
            set(organization_ids),
        )
        self.questionnaire.refresh_from_db()
        self.assertEqual(
            set(self.questionnaire.internal_organization_cache), set(cache_ids)
        )

    def test_assignment_listing_and_cache_include_parent_organizations(self):
        response = self.set_organizations([self.team])
        self.assertEqual(response.status_code, 200, response.data)
        self.assert_assignments(
            [self.team.pk], [self.root.pk, self.department.pk, self.team.pk]
        )
        listed = self.client.get(self.url("get"))
        self.assertEqual(listed.status_code, 200, listed.data)
        self.assertEqual(listed.data["count"], 1)
        self.assertEqual(listed.data["results"][0]["id"], str(self.team.external_id))
        self.assertEqual(listed.data["results"][0]["name"], "Consultation")

    def test_assignment_replaces_old_scope_and_empty_assignment_retains_root_scope(
        self,
    ):
        initial = self.set_organizations([self.team])
        self.assertEqual(initial.status_code, 200, initial.data)
        replaced = self.set_organizations([self.other_department])
        self.assertEqual(replaced.status_code, 200, replaced.data)
        self.assert_assignments(
            [self.other_department.pk], [self.root.pk, self.other_department.pk]
        )
        cleared = self.set_organizations([])
        self.assertEqual(cleared.status_code, 200, cleared.data)
        self.assert_assignments([], [self.root.pk])
        listed = self.client.get(self.url("get"))
        self.assertEqual(listed.status_code, 200, listed.data)
        self.assertEqual(listed.data, {"count": 0, "results": []})

    def test_invalid_or_cross_facility_assignment_rolls_back_existing_scope(self):
        initial = self.set_organizations([self.team])
        self.assertEqual(initial.status_code, 200, initial.data)
        other_facility = self.create_facility(user=self.admin)
        for invalid_id in (
            uuid4(),
            other_facility.default_internal_organization.external_id,
        ):
            with self.subTest(invalid_id=invalid_id):
                response = self.client.post(
                    self.url("set"),
                    {
                        "facility_organizations": [
                            str(self.other_department.external_id),
                            str(invalid_id),
                        ]
                    },
                    format="json",
                )
                self.assertEqual(response.status_code, 404, response.data)
                self.assert_assignments(
                    [self.team.pk], [self.root.pk, self.department.pk, self.team.pk]
                )

    def test_malformed_assignment_is_rejected_without_removing_existing_scope(self):
        initial = self.set_organizations([self.team])
        self.assertEqual(initial.status_code, 200, initial.data)
        for payload in ({}, {"facility_organizations": ["invalid-id"]}):
            with self.subTest(payload=payload):
                response = self.client.post(self.url("set"), payload, format="json")
                self.assertEqual(response.status_code, 400, response.data)
                self.assert_assignments(
                    [self.team.pk], [self.root.pk, self.department.pk, self.team.pk]
                )

    def test_facility_root_writer_can_manage_scope_without_superuser_access(self):
        writer = self.create_user()
        role = self.create_role_with_permissions(
            [QuestionnairePermissions.can_write_questionnaire.name]
        )
        self.attach_role_facility_organization_user(self.root, writer, role)
        self.client.force_authenticate(writer)
        response = self.set_organizations([self.department])
        self.assertEqual(response.status_code, 200, response.data)
        listed = self.client.get(self.url("get"))
        self.assertEqual(listed.status_code, 200, listed.data)
        self.assertEqual(
            [item["id"] for item in listed.data["results"]],
            [str(self.department.external_id)],
        )

    def test_readers_and_department_writers_cannot_manage_facility_scope(self):
        for permission, organization in (
            (QuestionnairePermissions.can_read_questionnaire.name, self.root),
            (QuestionnairePermissions.can_write_questionnaire.name, self.department),
        ):
            with self.subTest(permission=permission, organization=organization):
                user = self.create_user()
                role = self.create_role_with_permissions([permission])
                self.attach_role_facility_organization_user(organization, user, role)
                self.client.force_authenticate(user)
                assigned = self.set_organizations([self.team])
                listed = self.client.get(self.url("get"))
                self.assertEqual(assigned.status_code, 403, assigned.data)
                self.assertEqual(listed.status_code, 403, listed.data)
                self.assert_assignments([], [self.root.pk])

    def test_scope_endpoints_reject_other_questionnaire_contexts(self):
        for auth_context in ("instance", "user", "facility_organization"):
            with self.subTest(auth_context=auth_context):
                questionnaire = self.make_questionnaire(
                    auth_context=auth_context,
                    facility_organization=self.department
                    if auth_context == "facility_organization"
                    else None,
                )
                assigned = self.set_organizations([self.team], questionnaire)
                listed = self.client.get(self.url("get", questionnaire))
                self.assertEqual(assigned.status_code, 403, assigned.data)
                self.assertEqual(listed.status_code, 403, listed.data)
                self.assertFalse(
                    QuestionnaireFacilityOrganization.objects.filter(
                        questionnaire=questionnaire
                    ).exists()
                )

    def test_past_revision_scope_cannot_be_modified_or_listed(self):
        historical = self.make_questionnaire(latest_revision=self.questionnaire)
        assigned = self.set_organizations([self.team], historical)
        listed = self.client.get(self.url("get", historical))
        self.assertEqual(assigned.status_code, 403, assigned.data)
        self.assertEqual(listed.status_code, 403, listed.data)
        self.assertFalse(
            QuestionnaireFacilityOrganization.objects.filter(
                questionnaire=historical
            ).exists()
        )
