from django.conf import settings
from django.urls import reverse

from care.security.permissions.organization import (
    OrganizationPermissions,
)
from care.security.roles.role import ADMINISTRATOR
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
