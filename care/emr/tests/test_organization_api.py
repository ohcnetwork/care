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

    # Organaization List API Tests

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
        """Test that a regular user cannot list organizations."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

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
        self.assertContains(response, "Max depth reached (10)", status_code=400)

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
        self.assertContains(get_response, "Object not found", status_code=404)

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
            "User does not have the required permissions to update organizations",
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

    def test_get_only_parent_organizations(self):
        """Test that only parent organizations are returned."""
        self.client.force_authenticate(user=self.super_user)
        self.create_organization(
            user=self.super_user, name="Parent Org 1", org_type="govt"
        )
        self.create_organization(
            user=self.super_user,
            name="Child Org 1",
            org_type="team",
            parent=self.root_organization,
        )
        response = self.client.get(
            f"{self.url}?parent={self.root_organization.external_id}"
        )
        self.assertEqual(response.status_code, 200)

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
