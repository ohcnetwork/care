from copy import deepcopy
from uuid import uuid4

from django.test import SimpleTestCase
from django.urls import reverse
from model_bakery import baker
from pydantic import ValidationError

from care.emr.models.immunisation import ImmunizationPolicy
from care.emr.resources.immunisation.policy import ImmunizationPolicyTemplateSpec
from care.security.permissions.immunization import ImmunizationPermissions
from care.utils.tests.base import CareAPITestBase


class TestImmunizationPolicyAPI(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_super_user()
        self.client.force_authenticate(self.user)
        self.facility = self.create_facility(user=self.user)
        self.other_facility = self.create_facility(user=self.user)
        self.url = reverse("immunization-policy-list")
        self.template = {
            "is_group": True,
            "description": "Routine vaccination",
            "children": [
                {
                    "is_group": False,
                    "codes": [
                        {
                            "system": "http://test.care/vaccine",
                            "code": "vaccine",
                            "display": "Vaccine",
                        }
                    ],
                    "earliest_date": 0,
                    "due_date": 7,
                    "overdue_date": 14,
                    "dose_number": "1",
                }
            ],
        }

    def detail_url(self, policy):
        return reverse(
            "immunization-policy-detail",
            kwargs={"external_id": policy.external_id},
        )

    def data(self, **kwargs):
        return {
            "name": "Routine immunization schedule",
            "description": "First dose",
            "policy_template": deepcopy(self.template),
            **kwargs,
        }

    def make_policy(self, **kwargs):
        return baker.make(ImmunizationPolicy, **self.data(**kwargs))

    def grant(self, user, facility, *permissions):
        role = self.create_role_with_permissions(list(permissions))
        self.attach_role_facility_organization_user(
            facility.default_internal_organization, user, role
        )

    def test_create_global_policy_persists_nested_template_and_audit_users(self):
        response = self.client.post(self.url, self.data(), format="json")
        self.assertEqual(response.status_code, 200, response.data)
        policy = ImmunizationPolicy.objects.get(external_id=response.data["id"])
        self.assertIsNone(policy.facility)
        self.assertEqual(policy.name, "Routine immunization schedule")
        self.assertEqual(policy.created_by, self.user)
        self.assertEqual(policy.updated_by, self.user)
        self.assertEqual(policy.policy_template["children"][0]["due_date"], 7)
        self.assertEqual(
            self.client.get(self.detail_url(policy)).data["policy_template"],
            response.data["policy_template"],
        )

    def test_facility_admin_can_create_and_update_facility_policy(self):
        user = self.create_user()
        self.grant(
            user,
            self.facility,
            ImmunizationPermissions.can_write_immunization_policy.name,
            ImmunizationPermissions.can_read_immunization_policy.name,
        )
        self.client.force_authenticate(user)
        response = self.client.post(
            self.url,
            self.data(facility=str(self.facility.external_id)),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        policy = ImmunizationPolicy.objects.get(external_id=response.data["id"])
        self.assertEqual(policy.facility, self.facility)
        response = self.client.patch(
            self.detail_url(policy), self.data(name="Revised schedule"), format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        policy.refresh_from_db()
        self.assertEqual(policy.name, "Revised schedule")
        self.assertEqual(policy.updated_by, user)

    def test_global_policy_writes_require_superuser(self):
        policy = self.make_policy()
        user = self.create_user()
        self.grant(
            user,
            self.facility,
            ImmunizationPermissions.can_write_immunization_policy.name,
        )
        self.client.force_authenticate(user)
        self.assertEqual(
            self.client.post(self.url, self.data(), format="json").status_code, 403
        )
        self.assertEqual(
            self.client.patch(
                self.detail_url(policy), self.data(name="Denied"), format="json"
            ).status_code,
            403,
        )
        policy.refresh_from_db()
        self.assertEqual(policy.name, "Routine immunization schedule")
        self.assertEqual(ImmunizationPolicy.objects.count(), 1)

    def test_read_permission_does_not_grant_facility_policy_write(self):
        policy = self.make_policy(facility=self.facility)
        user = self.create_user()
        self.grant(
            user,
            self.facility,
            ImmunizationPermissions.can_read_immunization_policy.name,
        )
        self.client.force_authenticate(user)
        self.assertEqual(self.client.get(self.detail_url(policy)).status_code, 200)
        self.assertEqual(
            self.client.post(
                self.url,
                self.data(facility=str(self.facility.external_id)),
                format="json",
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.patch(
                self.detail_url(policy), self.data(name="Denied"), format="json"
            ).status_code,
            403,
        )

    def test_unrelated_facility_permissions_do_not_grant_access(self):
        policy = self.make_policy(facility=self.facility)
        user = self.create_user()
        self.grant(
            user,
            self.other_facility,
            ImmunizationPermissions.can_read_immunization_policy.name,
            ImmunizationPermissions.can_write_immunization_policy.name,
        )
        self.client.force_authenticate(user)
        self.assertEqual(self.client.get(self.detail_url(policy)).status_code, 403)
        self.assertEqual(
            self.client.get(
                self.url, {"facility": str(self.facility.external_id)}
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.patch(
                self.detail_url(policy), self.data(name="Denied"), format="json"
            ).status_code,
            403,
        )

    def test_default_list_contains_only_global_policies(self):
        global_policy = self.make_policy()
        self.make_policy(facility=self.facility)
        self.make_policy(facility=self.other_facility)
        self.client.force_authenticate(self.create_user())
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            [row["id"] for row in response.data["results"]],
            [str(global_policy.external_id)],
        )
        self.assertEqual(
            self.client.get(self.detail_url(global_policy)).status_code, 200
        )

    def test_facility_list_includes_global_and_own_policies(self):
        global_policy = self.make_policy()
        own_policy = self.make_policy(facility=self.facility)
        self.make_policy(facility=self.other_facility)
        response = self.client.get(
            self.url, {"facility": str(self.facility.external_id)}
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertCountEqual(
            [row["id"] for row in response.data["results"]],
            [str(global_policy.external_id), str(own_policy.external_id)],
        )

    def test_name_filter_is_case_insensitive_and_preserves_facility_scope(self):
        matching = self.make_policy(name="Routine CHILD vaccinations")
        self.make_policy(name="Adult vaccinations")
        self.make_policy(name="Child private schedule", facility=self.other_facility)
        response = self.client.get(self.url, {"name": "child"})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            [row["id"] for row in response.data["results"]],
            [str(matching.external_id)],
        )

    def test_missing_facility_is_rejected_before_creating_policy(self):
        response = self.client.post(
            self.url, self.data(facility=str(uuid4())), format="json"
        )
        self.assertEqual(response.status_code, 404, response.data)
        self.assertFalse(ImmunizationPolicy.objects.exists())
        self.assertEqual(
            self.client.get(self.url, {"facility": str(uuid4())}).status_code, 404
        )

    def test_invalid_nested_template_does_not_persist_policy(self):
        template = deepcopy(self.template)
        template["children"][0]["codes"] = []
        response = self.client.post(
            self.url, self.data(policy_template=template), format="json"
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(ImmunizationPolicy.objects.exists())

    def test_policy_cannot_be_deleted(self):
        policy = self.make_policy()
        self.assertEqual(self.client.delete(self.detail_url(policy)).status_code, 405)
        self.assertTrue(ImmunizationPolicy.objects.filter(pk=policy.pk).exists())


class TestImmunizationPolicyTemplate(SimpleTestCase):
    def test_group_can_omit_codes_and_contain_nested_groups(self):
        template = ImmunizationPolicyTemplateSpec.model_validate(
            {
                "is_group": True,
                "children": [{"is_group": True, "description": "Later doses"}],
            }
        )
        self.assertTrue(template.children[0].is_group)

    def test_nongroup_requires_codes(self):
        for extra in ({}, {"codes": []}):
            with (
                self.subTest(extra=extra),
                self.assertRaisesRegex(ValidationError, "Codes are required"),
            ):
                ImmunizationPolicyTemplateSpec.model_validate(
                    {"is_group": False, **extra}
                )

    def test_nongroup_cannot_contain_children(self):
        with self.assertRaisesRegex(
            ValidationError, "Only groups can contain children"
        ):
            ImmunizationPolicyTemplateSpec.model_validate(
                {"is_group": False, "children": [{"is_group": True}]}
            )

    def test_supplied_date_offsets_must_be_strictly_increasing(self):
        cases = [
            {"earliest_date": 7, "due_date": 7},
            {"due_date": 14, "overdue_date": 7},
            {"earliest_date": 7, "overdue_date": 0},
            {"earliest_date": 0, "due_date": 7, "overdue_date": 7},
        ]
        for dates in cases:
            with (
                self.subTest(dates=dates),
                self.assertRaisesRegex(ValidationError, "must be before"),
            ):
                ImmunizationPolicyTemplateSpec.model_validate(
                    {"is_group": True, **dates}
                )

    def test_negative_and_omitted_date_offsets_are_supported(self):
        for dates in (
            {},
            {"due_date": 0},
            {"earliest_date": -7, "overdue_date": 14},
            {"earliest_date": -14, "due_date": -7, "overdue_date": 0},
        ):
            with self.subTest(dates=dates):
                template = ImmunizationPolicyTemplateSpec.model_validate(
                    {"is_group": True, **dates}
                )
                for field, value in dates.items():
                    self.assertEqual(getattr(template, field), value)
