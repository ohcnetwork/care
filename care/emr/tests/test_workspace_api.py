from uuid import uuid4

from django.core.cache import cache
from django.urls import reverse

from care.emr.models.workspace import (
    Workspace,
    WorkspaceFacilityOrganization,
    WorkspaceOrganization,
    WorkSpaceUserDefault,
)
from care.security.permissions.workspace import WorkspacePermissions
from care.utils.tests.base import CareAPITestBase


class WorkspaceAPITests(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.admin = self.create_super_user()
        self.user = self.create_user()
        self.facility = self.create_facility(self.admin)
        self.root_org = self.create_facility_organization(
            self.facility, org_type="root"
        )
        self.department = self.create_facility_organization(
            self.facility, org_type="dept", parent=self.root_org
        )
        self.client.force_authenticate(self.admin)
        self.list_url = reverse("workspace-list")
        for user in (self.admin, self.user):
            self.addCleanup(cache.delete, WorkSpaceUserDefault.get_cache_key(user.id))

    def payload(self, **kwargs):
        return {
            "name": "Admissions",
            "description": "Admission dashboard",
            "template": {"widgets": [{"type": "encounters"}]},
            "status": "active",
            "auth_context": "instance",
            "inherited": False,
            **kwargs,
        }

    def workspace(self, **kwargs):
        return Workspace.objects.create(
            **{
                "name": "Admissions",
                "description": "Admission dashboard",
                "template": {"widgets": []},
                "status": "active",
                "auth_context": "instance",
                "created_by": self.admin,
                "updated_by": self.admin,
                **kwargs,
            }
        )

    def detail_url(self, workspace, action="detail"):
        return reverse(
            f"workspace-{action}",
            kwargs={"external_id": workspace.external_id},
        )

    def grant(self, *, permissions, organization=None, user=None):
        role = self.create_role_with_permissions(permissions)
        return self.attach_role_facility_organization_user(
            organization or self.root_org, user or self.user, role
        )

    def test_create_instance_workspace_and_record_audit_users(self):
        response = self.client.post(self.list_url, self.payload(), format="json")
        self.assertEqual(response.status_code, 200, response.data)
        workspace = Workspace.objects.get(external_id=response.data["id"])
        self.assertEqual(workspace.template, self.payload()["template"])
        self.assertEqual(workspace.status, "active")
        self.assertEqual(workspace.created_by, self.admin)
        self.assertEqual(workspace.updated_by, self.admin)

    def test_create_facility_workspace(self):
        response = self.client.post(
            self.list_url,
            self.payload(
                auth_context="facility", facility=str(self.facility.external_id)
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        workspace = Workspace.objects.get(external_id=response.data["id"])
        self.assertEqual(workspace.facility, self.facility)

    def test_create_department_workspace_includes_ancestor_access(self):
        response = self.client.post(
            self.list_url,
            self.payload(
                auth_context="facility_organization",
                facility_organization=str(self.department.external_id),
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        workspace = Workspace.objects.get(external_id=response.data["id"])
        self.assertEqual(workspace.facility, self.facility)
        self.assertEqual(workspace.facility_organization, self.department)
        self.assertCountEqual(
            workspace.internal_organization_cache,
            [self.root_org.id, self.department.id],
        )

    def test_create_user_workspace(self):
        self.grant(permissions=[WorkspacePermissions.can_write_workspace.name])
        self.client.force_authenticate(self.user)
        response = self.client.post(
            self.list_url,
            self.payload(auth_context="user", facility=str(self.facility.external_id)),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            Workspace.objects.get(external_id=response.data["id"]).created_by,
            self.user,
        )

    def test_regular_user_cannot_create_instance_workspace(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(self.list_url, self.payload(), format="json")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Workspace.objects.exists())

    def test_write_permission_is_required_in_the_requested_facility(self):
        other_facility = self.create_facility(self.admin)
        self.grant(permissions=[WorkspacePermissions.can_write_workspace.name])
        self.client.force_authenticate(self.user)
        response = self.client.post(
            self.list_url,
            self.payload(
                auth_context="facility", facility=str(other_facility.external_id)
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_missing_scope_and_unknown_identifiers_are_rejected(self):
        cases = [
            {"auth_context": "facility"},
            {"auth_context": "user"},
            {"auth_context": "facility_organization"},
            {"auth_context": "facility", "facility": str(uuid4())},
            {
                "auth_context": "facility_organization",
                "facility_organization": str(uuid4()),
            },
        ]
        for fields in cases:
            with self.subTest(fields=fields):
                response = self.client.post(
                    self.list_url, self.payload(**fields), format="json"
                )
                self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Workspace.objects.exists())

    def test_status_filter_and_status_update(self):
        active = self.workspace()
        self.workspace(name="Draft", status="draft")
        self.workspace(name="Archive", status="archived")
        response = self.client.get(self.list_url, {"status": "ACTIVE"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [obj["id"] for obj in response.data["results"]], [str(active.external_id)]
        )

        response = self.client.put(
            self.detail_url(active),
            self.payload(name="Archived admissions", status="archived"),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        active.refresh_from_db()
        self.assertEqual(active.status, "archived")
        self.assertEqual(active.name, "Archived admissions")

    def test_invalid_status_is_rejected(self):
        response = self.client.post(
            self.list_url, self.payload(status="unknown"), format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_list_filters_facility_context_and_name(self):
        matching = self.workspace(auth_context="facility", facility=self.facility)
        self.workspace(name="Other", auth_context="user", facility=self.facility)
        self.workspace(name="Admissions elsewhere")
        response = self.client.get(
            self.list_url,
            {
                "facility": str(self.facility.external_id),
                "auth_context": "facility",
                "name": "admiss",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [obj["id"] for obj in response.data["results"]], [str(matching.external_id)]
        )

    def test_user_only_sees_their_own_user_workspace(self):
        own = self.workspace(
            auth_context="user", facility=self.facility, created_by=self.user
        )
        other = self.workspace(auth_context="user", facility=self.facility)
        self.client.force_authenticate(self.user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [obj["id"] for obj in response.data["results"]], [str(own.external_id)]
        )
        self.assertEqual(self.client.get(self.detail_url(other)).status_code, 404)

    def test_department_reader_can_retrieve_but_cannot_edit_workspace(self):
        workspace = self.workspace(
            auth_context="facility_organization",
            facility=self.facility,
            facility_organization=self.department,
        )
        workspace.sync_facility_org_cache()
        self.grant(
            permissions=[WorkspacePermissions.can_read_workspace.name],
            organization=self.department,
        )
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get(self.detail_url(workspace)).status_code, 200)
        response = self.client.put(
            self.detail_url(workspace), self.payload(name="Changed"), format="json"
        )
        self.assertEqual(response.status_code, 403)
        workspace.refresh_from_db()
        self.assertEqual(workspace.name, "Admissions")

    def test_root_writer_can_manage_facility_workspace_without_a_read_role(self):
        workspace = self.workspace(auth_context="facility", facility=self.facility)
        self.grant(permissions=[WorkspacePermissions.can_write_workspace.name])
        self.client.force_authenticate(self.user)
        response = self.client.put(
            self.detail_url(workspace), self.payload(name="Changed"), format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        workspace.refresh_from_db()
        self.assertEqual(workspace.updated_by, self.user)
        self.assertEqual(
            self.client.delete(self.detail_url(workspace)).status_code, 204
        )
        self.assertFalse(Workspace.objects.filter(pk=workspace.pk).exists())

    def test_user_workspace_is_editable_only_by_its_creator(self):
        workspace = self.workspace(auth_context="user", facility=self.facility)
        self.grant(permissions=[WorkspacePermissions.can_write_workspace.name])
        self.client.force_authenticate(self.user)
        self.assertEqual(
            self.client.put(
                self.detail_url(workspace), self.payload(), format="json"
            ).status_code,
            404,
        )
        workspace.created_by = self.user
        workspace.save(update_fields=["created_by"])
        response = self.client.put(
            self.detail_url(workspace), self.payload(name="Personal"), format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)

    def test_set_facility_organizations_replaces_links_and_ancestor_cache(self):
        workspace = self.workspace(auth_context="facility", facility=self.facility)
        url = self.detail_url(workspace, "set-facility-organizations")
        response = self.client.post(
            url,
            {
                "facility_organizations": [
                    str(self.department.external_id),
                    str(self.root_org.external_id),
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        workspace.refresh_from_db()
        self.assertCountEqual(
            workspace.internal_organization_cache,
            [self.root_org.id, self.department.id],
        )
        response = self.client.get(
            self.detail_url(workspace, "get-facility-organizations")
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        response = self.client.post(url, {"facility_organizations": []}, format="json")
        self.assertEqual(response.status_code, 200)
        workspace.refresh_from_db()
        self.assertEqual(workspace.internal_organization_cache, [])
        self.assertFalse(
            WorkspaceFacilityOrganization.objects.filter(workspace=workspace).exists()
        )

    def test_cross_facility_assignment_rolls_back_existing_links(self):
        workspace = self.workspace(auth_context="facility", facility=self.facility)
        WorkspaceFacilityOrganization.objects.create(
            workspace=workspace, organization=self.department
        )
        workspace.sync_facility_org_cache()
        other_org = self.create_facility_organization(
            self.create_facility(self.admin), org_type="root"
        )
        response = self.client.post(
            self.detail_url(workspace, "set-facility-organizations"),
            {"facility_organizations": [str(other_org.external_id)]},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            WorkspaceFacilityOrganization.objects.get(workspace=workspace).organization,
            self.department,
        )
        workspace.refresh_from_db()
        self.assertCountEqual(
            workspace.internal_organization_cache,
            [self.root_org.id, self.department.id],
        )

    def test_instance_organization_assignment_controls_visibility(self):
        parent = self.create_organization(org_type="root")
        child = self.create_organization(org_type="team", parent=parent)
        workspace = self.workspace()
        response = self.client.post(
            self.detail_url(workspace, "set-organizations"),
            {"organizations": [str(child.external_id)]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        workspace.refresh_from_db()
        self.assertCountEqual(workspace.organization_cache, [parent.id, child.id])
        self.assertEqual(
            WorkspaceOrganization.objects.get(workspace=workspace).organization, child
        )
        role = self.create_role_with_permissions(
            [WorkspacePermissions.can_read_workspace.name]
        )
        self.attach_role_organization_user(parent, self.user, role)
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get(self.detail_url(workspace)).status_code, 200)
        response = self.client.put(
            self.detail_url(workspace), self.payload(), format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_organization_actions_reject_the_wrong_workspace_scope(self):
        instance = self.workspace()
        facility = self.workspace(auth_context="facility", facility=self.facility)
        cases = [
            (instance, "set-facility-organizations", {"facility_organizations": []}),
            (facility, "set-organizations", {"organizations": []}),
        ]
        for workspace, action, payload in cases:
            with self.subTest(action=action):
                response = self.client.post(
                    self.detail_url(workspace, action), payload, format="json"
                )
                self.assertEqual(response.status_code, 403)
                response = self.client.get(
                    self.detail_url(workspace, action.replace("set-", "get-"))
                )
                self.assertEqual(response.status_code, 403)

    def test_instance_organization_endpoints_list_replace_clear_and_rollback_links(
        self,
    ):
        parent = self.create_organization(org_type="root")
        first = self.create_organization(org_type="team", parent=parent)
        replacement = self.create_organization(org_type="team", parent=parent)
        workspace = self.workspace()
        set_url = self.detail_url(workspace, "set-organizations")
        get_url = self.detail_url(workspace, "get-organizations")
        response = self.client.post(
            set_url, {"organizations": [str(first.external_id)]}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        listed = self.client.get(get_url)
        self.assertEqual(listed.status_code, 200, listed.data)
        self.assertEqual(listed.data["count"], 1)
        self.assertEqual(listed.data["results"][0]["id"], str(first.external_id))

        response = self.client.post(
            set_url, {"organizations": [str(uuid4())]}, format="json"
        )
        self.assertEqual(response.status_code, 404)
        workspace.refresh_from_db()
        self.assertCountEqual(workspace.organization_cache, [parent.pk, first.pk])
        self.assertEqual(
            WorkspaceOrganization.objects.get(workspace=workspace).organization,
            first,
        )

        response = self.client.post(
            set_url, {"organizations": [str(replacement.external_id)]}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        workspace.refresh_from_db()
        self.assertCountEqual(workspace.organization_cache, [parent.pk, replacement.pk])
        self.assertEqual(
            [row["id"] for row in self.client.get(get_url).data["results"]],
            [str(replacement.external_id)],
        )
        response = self.client.post(set_url, {"organizations": []}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        workspace.refresh_from_db()
        self.assertEqual(workspace.organization_cache, [])
        self.assertEqual(self.client.get(get_url).data["count"], 0)

    def test_default_attributes_are_replaced_per_attribute_and_user(self):
        workspace = self.workspace(
            auth_context="user", facility=self.facility, created_by=self.user
        )
        WorkSpaceUserDefault.objects.create(
            workspace=workspace, user=self.admin, attribute="view", value="admin"
        )
        self.client.force_authenticate(self.user)
        url = self.detail_url(workspace, "set-default-attributes")
        for payload in (
            {"attribute": "view", "value": "list"},
            {"attribute": "view", "value": "board"},
            {"attribute": "sort", "value": "recent"},
            {"value": "default"},
        ):
            response = self.client.post(url, payload, format="json")
            self.assertEqual(response.status_code, 200, response.data)
        response = self.client.get(reverse("workspace-get-user-default-attributes"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(
            {obj["attribute"]: obj["value"] for obj in response.data["results"]},
            {"view": "board", "sort": "recent", None: "default"},
        )
        self.assertTrue(
            all(
                obj["workspace"]["id"] == str(workspace.external_id)
                for obj in response.data["results"]
            )
        )
        self.assertEqual(
            WorkSpaceUserDefault.objects.get(user=self.admin).value, "admin"
        )

    def test_default_attributes_cache_is_invalidated_on_workspace_and_default_changes(
        self,
    ):
        workspace = self.workspace()
        default = WorkSpaceUserDefault.objects.create(
            workspace=workspace, user=self.admin, attribute="view", value="list"
        )
        url = reverse("workspace-get-user-default-attributes")
        self.assertEqual(self.client.get(url).data["results"][0]["value"], "list")
        default.value = "board"
        default.save(update_fields=["value"])
        self.assertEqual(self.client.get(url).data["results"][0]["value"], "board")
        workspace.name = "Renamed"
        workspace.save(update_fields=["name"])
        self.assertEqual(
            self.client.get(url).data["results"][0]["workspace"]["name"], "Renamed"
        )
        default.delete()
        self.assertEqual(self.client.get(url).data["count"], 0)

    def test_unauthenticated_requests_are_denied(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.list_url).status_code, 403)
