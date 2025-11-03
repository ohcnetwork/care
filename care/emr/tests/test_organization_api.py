from django.conf import settings
from django.urls import reverse

from care.security.permissions.organization import (
    OrganizationPermissions,
)
from care.security.roles.role import ADMINISTRATOR, STAFF_ROLE
from care.utils.tests.base import CareAPITestBase


class OrganizationAPITestCase(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.super_user = self.create_super_user()
        self.user = self.create_user()
        self.administrator_role = self.create_role_with_permissions(
            role_name=ADMINISTRATOR.name,
            permissions=[
                OrganizationPermissions.can_view_organization.name,
                OrganizationPermissions.can_manage_organization_users.name,
                OrganizationPermissions.can_list_organization_users.name,
            ],
        )
        self.root_organization = self.create_organization(
            user=self.super_user, name="Parent Organization", org_type="govt"
        )

        self.url = reverse("organization-list")

    def get_detail_url(self, org_external_id):
        return reverse(
            "organization-detail",
            kwargs={"external_id": org_external_id},
        )

    # Organization List API Tests

    def test_list_organizations_as_super_user(self):
        """Test that a super user can list organizations."""
        self.client.force_authenticate(user=self.super_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len(response.data["results"]), 1, "Super user should see one organization"
        )
        self.assertEqual(
            response.data["results"][0]["id"],
            str(self.root_organization.external_id),
            "Super user should see the root organization",
        )

    def test_list_organizations_as_user(self):
        """Test that a regular user can list organizations."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["results"][0]["id"], str(self.root_organization.external_id)
        )

    # Organization Create API Tests

    def test_create_root_organization_as_super_user(self):
        """Test that a super user can create root organization."""
        self.client.force_authenticate(user=self.super_user)
        data = {
            "name": "New Govt Organization",
            "description": "This is a new govt organization.",
            "org_type": "govt",
        }
        response = self.client.post(self.url, data, format="json")
        org_id = response.data.get("id")
        get_response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len(
                [
                    org
                    for org in get_response.data["results"]
                    if org["id"] == str(org_id)
                ]
            ),
            1,
        )

    def test_create_root_organization_as_user(self):
        """Test that a user other than super user cannot create a root organization."""
        self.attach_role_organization_user(
            self.root_organization, self.user, self.administrator_role
        )
        self.client.force_authenticate(user=self.user)
        data = {
            "name": "New Govt Organization",
            "description": "This is a new govt organization.",
            "org_type": "govt",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "Root Organizations can only be created by the superadmin",
            status_code=403,
        )

    def test_create_child_organization_as_super_user(self):
        """Test that a super user can create a child organization."""
        self.client.force_authenticate(user=self.super_user)
        data = {
            "name": "Child Organization",
            "description": "This is a child organization.",
            "org_type": "govt",
            "parent": str(self.root_organization.external_id),
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["parent"]["id"], str(self.root_organization.external_id)
        )
        get_response = self.client.get(self.get_detail_url(response.data["id"]))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(
            get_response.data["parent"]["id"], str(self.root_organization.external_id)
        )

    def test_create_organization_with_org_type_as_user(self):
        """Test that a user cannot create a organization with org_type (govt/role)."""
        self.attach_role_organization_user(
            self.root_organization, self.user, self.administrator_role
        )
        self.client.force_authenticate(user=self.user)
        data = {
            "name": "New Govt Organization",
            "description": "This is a new govt organization.",
            "org_type": "govt",
            "parent": str(self.root_organization.external_id),
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "Organization Type cannot be created", status_code=403
        )

    def test_create_child_organization_as_user(self):
        """Test that a user other than super user cannot create a child organization."""
        self.attach_role_organization_user(
            self.root_organization, self.user, self.administrator_role
        )
        self.client.force_authenticate(user=self.user)
        data = {
            "name": "Child Organization",
            "description": "This is a child organization.",
            "org_type": "team",
            "parent": str(self.root_organization.external_id),
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "User does not have the required permissions to create organizations",
            status_code=403,
        )

    def test_create_organization_with_duplicate_name(self):
        """Test that a user cannot create a organization with a duplicate name."""
        self.client.force_authenticate(user=self.super_user)
        data = {
            "name": "Parent Organization",
            "description": "This is a duplicate organization.",
            "org_type": "govt",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response, "Organization already exists with same name", status_code=400
        )

    def test_create_organizations_exceeding_max_depth(self):
        """Test that a user cannot create an organization exceeding max depth."""
        self.client.force_authenticate(user=self.super_user)
        parent_org = self.create_organization(
            user=self.super_user, name="Parent Org", org_type="govt"
        )
        for i in range(settings.ORGANIZATION_MAX_DEPTH):
            child_org = self.create_organization(
                user=self.super_user,
                name=f"Child Org {i}",
                org_type="govt",
                parent=parent_org,
            )
            parent_org = child_org
        response = self.client.post(
            self.url,
            {
                "name": "New Child Organization",
                "description": "This is a new child organization.",
                "org_type": "govt",
                "parent": str(parent_org.external_id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            f"Max depth reached ({settings.ORGANIZATION_MAX_DEPTH})",
            status_code=400,
        )

    # Organization Update API Tests

    def test_update_organization_as_super_user(self):
        """Test that a super user can update an organization."""
        self.client.force_authenticate(user=self.super_user)
        data = {
            "active": True,
            "name": "Updated Organization",
            "description": "This is an updated organization.",
            "org_type": "govt",
        }
        response = self.client.put(
            self.get_detail_url(self.root_organization.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        get_update_response = self.client.get(
            self.get_detail_url(self.root_organization.external_id)
        )
        self.assertEqual(get_update_response.status_code, 200)
        self.assertEqual(get_update_response.data["name"], response.data["name"])

    def test_update_organization_with_org_type_as_user(self):
        """Test that a user cannot update an organization."""
        self.attach_role_organization_user(
            self.root_organization, self.user, self.administrator_role
        )
        self.client.force_authenticate(user=self.user)
        data = {
            "active": True,
            "name": "Updated Organization",
            "description": "This is an updated organization.",
            "org_type": "govt",
        }
        response = self.client.put(
            self.get_detail_url(self.root_organization.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "Organization Type cannot be updated",
            status_code=403,
        )

    def test_update_organization_without_permission(self):
        """Test that a user without permission cannot update an organization."""
        self.attach_role_organization_user(
            self.root_organization, self.user, self.administrator_role
        )
        self.child_organization = self.create_organization(
            user=self.super_user,
            name="Child Organization",
            org_type="team",
            parent=self.root_organization,
        )
        self.client.force_authenticate(user=self.user)
        data = {
            "active": True,
            "name": "Updated Organization",
            "description": "This is an updated organization.",
            "org_type": "team",
        }
        response = self.client.put(
            self.get_detail_url(self.child_organization.external_id),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "User does not have the required permissions to update organizations",
            status_code=403,
        )

    # Organization Delete API Tests

    def test_delete_organization_as_super_user(self):
        """Test that a super user can delete an organization."""
        self.client.force_authenticate(user=self.super_user)
        response = self.client.delete(
            self.get_detail_url(self.root_organization.external_id)
        )
        self.assertEqual(response.status_code, 204)
        get_response = self.client.get(
            self.get_detail_url(self.root_organization.external_id)
        )
        self.assertEqual(get_response.status_code, 404)
        self.assertContains(
            get_response, "No Organization matches the given query.", status_code=404
        )

    def test_delete_organization_with_org_type_as_user(self):
        """Test that a user cannot delete an organization."""
        self.attach_role_organization_user(
            self.root_organization, self.user, self.administrator_role
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(
            self.get_detail_url(self.root_organization.external_id)
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "Organization Type cannot be deleted",
            status_code=403,
        )

    def test_delete_organization_without_permission(self):
        """Test that a user without permission cannot delete an organization."""
        self.attach_role_organization_user(
            self.root_organization, self.user, self.administrator_role
        )
        self.child_organization = self.create_organization(
            user=self.super_user,
            name="Child Organization",
            org_type="team",
            parent=self.root_organization,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(
            self.get_detail_url(self.child_organization.external_id)
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "User does not have the required permissions to delete organizations",
            status_code=403,
        )

    def test_delete_organization_with_children(self):
        """Test that a user cannot delete an organization with children."""
        self.client.force_authenticate(user=self.super_user)
        self.create_organization(
            user=self.super_user,
            name="Child Organization",
            org_type="team",
            parent=self.root_organization,
        )
        response = self.client.delete(
            self.get_detail_url(self.root_organization.external_id)
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response, "Cannot delete organization with children", status_code=403
        )

    # Organization Filtering Tests

    def test_otp_user_can_only_access_govt_organizations(self):
        """Test that OTP users can only access government organizations."""
        # Create a user with is_alternative_login flag
        otp_user = self.create_user()
        otp_user.is_alternative_login = True
        otp_user.save()

        self.create_organization(user=self.super_user, name="Govt Org", org_type="govt")
        self.create_organization(user=self.super_user, name="Team Org", org_type="team")

        self.client.force_authenticate(user=otp_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        org_types = [org["org_type"] for org in response.data["results"]]
        self.assertTrue(all(org_type == "govt" for org_type in org_types))
        self.assertNotIn("team", org_types)

    def test_filter_organizations_by_parent(self):
        """Test that organizations can be filtered by parent."""
        self.client.force_authenticate(user=self.super_user)
        self.create_organization(
            user=self.super_user, name="Parent Org 1", org_type="govt"
        )
        child_org = self.create_organization(
            user=self.super_user,
            name="Child Org 1",
            org_type="team",
            parent=self.root_organization,
        )
        response = self.client.get(
            f"{self.url}?parent={self.root_organization.external_id}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], str(child_org.external_id))

    def test_list_organizations_filtered_by_permission(self):
        """Test that organizations can be filtered by user permissions."""
        org1 = self.create_organization(
            user=self.super_user, name="Org 1", org_type="govt"
        )
        self.create_organization(user=self.super_user, name="Org 2", org_type="team")
        role = self.create_role_with_permissions(
            permissions=[
                OrganizationPermissions.can_view_organization.name,
            ],
            role_name=STAFF_ROLE.name,
        )
        # Assign permissions to the user
        self.attach_role_organization_user(org1, self.user, role)
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            f"{self.url}?permission={OrganizationPermissions.can_view_organization.name}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            str(org1.external_id), [org["id"] for org in response.data["results"]]
        )

    def test_list_organizations_filtered_by_org_type(self):
        """Test that organizations can be filtered by org_type."""
        self.client.force_authenticate(user=self.user)
        self.create_organization(user=self.super_user, name="Govt Org", org_type="govt")
        self.create_organization(user=self.super_user, name="Team Org", org_type="team")
        response = self.client.get(f"{self.url}?org_type=govt")
        self.assertEqual(response.status_code, 200)
        org_types = [org["org_type"] for org in response.data["results"]]
        self.assertTrue(all(org_type == "govt" for org_type in org_types))

    def test_list_organizations_filtered_by_name(self):
        """Test that organizations can be filtered by name."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"{self.url}?name=Parent Organization")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(self.root_organization.external_id)
        )

    def test_list_organizations_filtered_by_parent(self):
        """Test that organizations can be filtered by parent."""
        self.client.force_authenticate(user=self.super_user)
        self.create_organization(
            user=self.super_user, name="Unrelated Org", org_type="team"
        )
        child_org = self.create_organization(
            user=self.super_user,
            name="Child Org 1",
            org_type="team",
            parent=self.root_organization,
        )
        response = self.client.get(
            f"{self.url}?parent={self.root_organization.external_id}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], str(child_org.external_id))

    def test_list_organizations_filtered_by_level_cache(self):
        """Test that organizations can be filtered by level_cache."""
        self.client.force_authenticate(user=self.super_user)
        org2 = self.create_organization(
            user=self.super_user,
            name="Child Org 1",
            org_type="team",
            parent=self.root_organization,
        )
        response = self.client.get(f"{self.url}?level_cache=1")
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            str(org2.external_id), [org["id"] for org in response.data["results"]]
        )
        self.assertNotIn(
            str(self.root_organization.external_id),
            [org["id"] for org in response.data["results"]],
        )

    def test_list_organizations_filtered_by_mine(self):
        """Test that organizations can be filtered by mine."""
        self.client.force_authenticate(user=self.user)
        org1 = self.create_organization(
            user=self.super_user, name="Govt Org", org_type="govt"
        )
        self.create_organization(user=self.super_user, name="Team Org", org_type="team")
        self.attach_role_organization_user(org1, self.user, self.administrator_role)
        response = self.client.get(f"{self.url}mine/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            str(org1.external_id), [org["id"] for org in response.data["results"]]
        )


class OrganizationUsersTestCase(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.super_user = self.create_super_user()
        self.user = self.create_user()
        self.administrator_role = self.create_role_with_permissions(
            role_name=ADMINISTRATOR.name,
            permissions=[
                OrganizationPermissions.can_view_organization.name,
                OrganizationPermissions.can_manage_organization_users.name,
                OrganizationPermissions.can_list_organization_users.name,
            ],
        )
        self.root_organization = self.create_organization(
            user=self.super_user, name="Parent Organization", org_type="govt"
        )

    def get_url(self, organization_external_id):
        """Get the URL for the organization users API."""
        return reverse(
            "organization-users-list",
            kwargs={"organization_external_id": str(organization_external_id)},
        )

    def get_detail_url(self, organization_external_id, user_external_id):
        """Get the URL for a specific organization user."""
        return reverse(
            "organization-users-detail",
            kwargs={
                "organization_external_id": str(organization_external_id),
                "external_id": str(user_external_id),
            },
        )

    # Adding Users to Organization

    def test_add_user_to_organization_as_super_user(self):
        """Test that a super user can add a user to an organization."""
        self.client.force_authenticate(user=self.super_user)
        data = {
            "user": str(self.user.external_id),
            "role": str(self.administrator_role.external_id),
        }
        response = self.client.post(
            self.get_url(self.root_organization.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["id"], str(self.user.external_id))
        self.assertEqual(
            response.data["role"]["id"], str(self.administrator_role.external_id)
        )
        get_response = self.client.get(self.get_url(self.root_organization.external_id))
        self.assertEqual(get_response.status_code, 200)
        self.assertIn(
            str(self.user.external_id),
            [user["user"]["id"] for user in get_response.data["results"]],
        )

    def test_add_user_to_organization_as_user_with_permission(self):
        """Test that a user with permission can add a user to an organization."""
        self.attach_role_organization_user(
            self.root_organization, self.user, self.administrator_role
        )
        new_user = self.create_user()
        self.client.force_authenticate(user=self.user)
        data = {
            "user": str(new_user.external_id),
            "role": str(self.administrator_role.external_id),
        }
        response = self.client.post(
            self.get_url(self.root_organization.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["id"], str(new_user.external_id))
        self.assertEqual(
            response.data["role"]["id"], str(self.administrator_role.external_id)
        )
        get_response = self.client.get(self.get_url(self.root_organization.external_id))
        self.assertEqual(get_response.status_code, 200)
        self.assertIn(
            str(new_user.external_id),
            [user["user"]["id"] for user in get_response.data["results"]],
        )

    def test_add_user_to_organization_as_user_without_permission(self):
        """Test that a user without permission cannot add a user to an organization."""
        self.client.force_authenticate(user=self.user)
        new_user = self.create_user()
        data = {
            "user": str(new_user.external_id),
            "role": str(self.administrator_role.external_id),
        }
        response = self.client.post(
            self.get_url(self.root_organization.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "User does not have permission for this action",
            status_code=403,
        )

    def test_add_user_to_organization_with_higher_role(self):
        """Test that a user cannot add another user with a higher role."""
        self.attach_role_organization_user(
            self.root_organization, self.user, self.administrator_role
        )
        new_user = self.create_user()
        higher_role = self.create_role_with_permissions(
            permissions=[
                OrganizationPermissions.can_manage_organization.name,
            ],
            role_name="Higher Role",
        )
        self.client.force_authenticate(user=self.user)
        data = {
            "user": str(new_user.external_id),
            "role": str(higher_role.external_id),
        }
        response = self.client.post(
            self.get_url(self.root_organization.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "User does not have permission for this action",
            status_code=403,
        )

    def test_add_user_to_the_same_organization(self):
        """Test that a user cannot add a user to the same organization twice."""
        self.client.force_authenticate(user=self.super_user)
        self.attach_role_organization_user(
            self.root_organization, self.user, self.administrator_role
        )
        data = {
            "user": str(self.user.external_id),
            "role": str(self.administrator_role.external_id),
        }
        response = self.client.post(
            self.get_url(self.root_organization.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "User association already exists",
            status_code=400,
        )

    def test_add_user_to_child_organization_already_linked_to_parent(self):
        """Test that cannot add a user to a child organization already linked to parent."""
        self.client.force_authenticate(user=self.super_user)
        child_organization = self.create_organization(
            user=self.super_user,
            name="Child Organization",
            org_type="team",
            parent=self.root_organization,
        )
        self.attach_role_organization_user(
            self.root_organization, self.user, self.administrator_role
        )
        data = {
            "user": str(self.user.external_id),
            "role": str(self.administrator_role.external_id),
        }
        response = self.client.post(
            self.get_url(child_organization.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "User is already linked to a parent organization",
            status_code=400,
        )

    def test_add_user_to_parent_organization_already_linked_to_child(self):
        """Test that cannot add a user to a parent organization already linked to child."""
        self.client.force_authenticate(user=self.super_user)
        child_organization = self.create_organization(
            user=self.super_user,
            name="Child Organization",
            org_type="team",
            parent=self.root_organization,
        )
        self.attach_role_organization_user(
            child_organization, self.user, self.administrator_role
        )
        data = {
            "user": str(self.user.external_id),
            "role": str(self.administrator_role.external_id),
        }
        response = self.client.post(
            self.get_url(self.root_organization.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response, "User has association to some child organization", status_code=400
        )

    # Removing Users from Organization

    def test_remove_user_from_organization_as_super_user(self):
        """Test that a super user can remove a user from an organization."""
        org_user = self.attach_role_organization_user(
            self.root_organization, self.user, self.administrator_role
        )
        self.client.force_authenticate(user=self.super_user)
        response = self.client.delete(
            self.get_detail_url(
                self.root_organization.external_id, org_user.external_id
            )
        )
        self.assertEqual(response.status_code, 204)
        get_response = self.client.get(
            self.get_detail_url(
                self.root_organization.external_id, org_user.external_id
            )
        )
        self.assertEqual(get_response.status_code, 404)

    def test_remove_user_from_organization_as_user_with_permission(self):
        """Test that a user with permission can remove a user from an organization."""
        self.attach_role_organization_user(
            self.root_organization, self.user, self.administrator_role
        )
        user = self.create_user()
        org_user2 = self.attach_role_organization_user(
            self.root_organization, user, self.administrator_role
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(
            self.get_detail_url(
                self.root_organization.external_id, org_user2.external_id
            )
        )
        self.assertEqual(response.status_code, 204)
        get_response = self.client.get(
            self.get_detail_url(
                self.root_organization.external_id, org_user2.external_id
            )
        )
        self.assertEqual(get_response.status_code, 404)

    def test_remove_user_from_organization_as_user_without_permission(self):
        """Test that a user without permission cannot remove a user from an organization."""
        role = self.create_role_with_permissions(
            role_name=STAFF_ROLE.name,
            permissions=[
                OrganizationPermissions.can_view_organization.name,
                OrganizationPermissions.can_list_organization_users.name,
            ],
        )
        new_user = self.create_user()
        org_user = self.attach_role_organization_user(
            self.root_organization, new_user, role
        )
        self.attach_role_organization_user(self.root_organization, self.user, role)
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(
            self.get_detail_url(
                self.root_organization.external_id, org_user.external_id
            )
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "User does not have permission for this action",
            status_code=403,
        )

    # getting User Details in Organization

    def test_get_users_in_organization_as_super_user(self):
        """Test that a super user can get users in an organization."""
        self.client.force_authenticate(user=self.super_user)
        org_user = self.attach_role_organization_user(
            self.root_organization, self.user, self.administrator_role
        )
        response = self.client.get(
            self.get_detail_url(
                self.root_organization.external_id, org_user.external_id
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["id"], str(self.user.external_id))

    def test_get_users_in_organization_as_user_with_permission(self):
        """Test that a user with permission can get users in an organization."""
        self.attach_role_organization_user(
            self.root_organization, self.user, self.administrator_role
        )
        self.client.force_authenticate(user=self.user)
        new_user = self.create_user()
        org_user = self.attach_role_organization_user(
            self.root_organization, new_user, self.administrator_role
        )

        response = self.client.get(
            self.get_detail_url(
                self.root_organization.external_id, org_user.external_id
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["id"], str(new_user.external_id))

    def test_get_users_in_organization_as_user_without_permission(self):
        """Test that a user without permission cannot get users in an organization."""

        new_user = self.create_user()
        role = self.create_role_with_permissions(
            role_name=STAFF_ROLE.name,
            permissions=[
                OrganizationPermissions.can_view_organization.name,
            ],
        )
        self.client.force_authenticate(user=self.user)
        org_user = self.attach_role_organization_user(
            self.root_organization, new_user, role
        )
        response = self.client.get(
            self.get_detail_url(
                self.root_organization.external_id, org_user.external_id
            )
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "User does not have the required permissions to list users",
            status_code=403,
        )

    # getting User List in Organization

    def test_list_users_in_organization_as_super_user(self):
        """Test that a super user can list users in an organization."""
        org_user = self.attach_role_organization_user(
            self.root_organization, self.user, self.administrator_role
        )
        self.client.force_authenticate(user=self.super_user)
        response = self.client.get(self.get_url(self.root_organization.external_id))
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            str(org_user.external_id),
            [user["id"] for user in response.data["results"]],
        )

    def test_list_users_in_organization_as_user_with_permission(self):
        """Test that a user with permission can list users in an organization."""
        self.attach_role_organization_user(
            self.root_organization, self.user, self.administrator_role
        )
        new_user = self.create_user()
        org_user = self.attach_role_organization_user(
            self.root_organization, new_user, self.administrator_role
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.get_url(self.root_organization.external_id))
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            str(org_user.external_id),
            [user["id"] for user in response.data["results"]],
        )

    def test_list_users_in_organization_as_user_without_permission(self):
        """Test that a user without permission cannot list users in an organization."""
        new_user = self.create_user()
        role = self.create_role_with_permissions(
            role_name=STAFF_ROLE.name,
            permissions=[
                OrganizationPermissions.can_view_organization.name,
            ],
        )
        self.attach_role_organization_user(self.root_organization, new_user, role)
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.get_url(self.root_organization.external_id))
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "User does not have the required permissions to list users",
            status_code=403,
        )

    # getting User update in Organization

    def test_update_user_in_organization_as_super_user(self):
        """Test that a super user can update a user in an organization."""
        self.create_role_with_permissions(
            role_name=STAFF_ROLE.name,
            permissions=[
                OrganizationPermissions.can_view_organization.name,
            ],
        )
        org_user = self.attach_role_organization_user(
            self.root_organization, self.user, self.administrator_role
        )
        self.client.force_authenticate(user=self.super_user)
        updated_data = {
            "role": str(self.administrator_role.external_id),
        }
        response = self.client.put(
            self.get_detail_url(
                self.root_organization.external_id, org_user.external_id
            ),
            updated_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(
                self.root_organization.external_id, org_user.external_id
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(
            get_response.data["role"]["id"], str(self.administrator_role.external_id)
        )

    def test_update_user_in_organization_as_user_with_permission(self):
        """Test that a user with permission can update a user in an organization."""
        self.attach_role_organization_user(
            self.root_organization, self.user, self.administrator_role
        )
        new_user = self.create_user(
            username="NewUser",
        )
        role = self.create_role_with_permissions(
            role_name=STAFF_ROLE.name,
            permissions=[
                OrganizationPermissions.can_view_organization.name,
                OrganizationPermissions.can_list_organization_users.name,
            ],
        )
        org_user = self.attach_role_organization_user(
            self.root_organization, new_user, role
        )
        self.client.force_authenticate(user=self.user)
        updated_data = {
            "role": str(self.administrator_role.external_id),
        }
        response = self.client.put(
            self.get_detail_url(
                self.root_organization.external_id, org_user.external_id
            ),
            updated_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(
                self.root_organization.external_id, org_user.external_id
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(
            get_response.data["role"]["id"], str(self.administrator_role.external_id)
        )

    def test_update_user_in_organization_as_user_without_permission(self):
        """Test that a user without permission cannot update a user in an organization."""
        new_user = self.create_user()
        role = self.create_role_with_permissions(
            role_name=STAFF_ROLE.name,
            permissions=[
                OrganizationPermissions.can_view_organization.name,
            ],
        )
        org_user = self.attach_role_organization_user(
            self.root_organization, new_user, role
        )
        self.client.force_authenticate(user=self.user)
        updated_data = {
            "role": str(self.administrator_role.external_id),
        }
        response = self.client.put(
            self.get_detail_url(
                self.root_organization.external_id, org_user.external_id
            ),
            updated_data,
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "User does not have the required permissions to list users",
            status_code=403,
        )

    def test_update_user_in_organization_with_higher_role(self):
        """Test that a user cannot update another user with a higher role."""
        role = self.create_role_with_permissions(
            role_name=STAFF_ROLE.name,
            permissions=[
                OrganizationPermissions.can_view_organization.name,
                OrganizationPermissions.can_list_organization_users.name,
            ],
        )
        self.attach_role_organization_user(self.root_organization, self.user, role)
        new_user = self.create_user()
        org_user = self.attach_role_organization_user(
            self.root_organization, new_user, role
        )
        self.client.force_authenticate(user=self.user)
        updated_data = {
            "role": str(self.administrator_role.external_id),
        }
        response = self.client.put(
            self.get_detail_url(
                self.root_organization.external_id, org_user.external_id
            ),
            updated_data,
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "User does not have permission for this action",
            status_code=403,
        )
