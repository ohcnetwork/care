from django.urls import reverse
from rest_framework import status

from care.emr.models.organization import OrganizationUser
from care.security.permissions.organization import OrganizationPermissions
from care.security.permissions.user import UserPermissions
from care.security.roles.role import (
    RoleContext,
)
from care.utils.tests.base import CareAPITestBase


class ManagingOrganizationAPITestCase(CareAPITestBase):
    """Tests for the managing_organization action on OrganizationViewSet."""

    def setUp(self):
        super().setUp()
        self.super_user = self.create_super_user()
        self.user = self.create_user()

        self.role_org_admin_role = self.create_role_with_permissions(
            role_name="Test Role Org Admin",
            permissions=[
                OrganizationPermissions.can_view_organization.name,
                OrganizationPermissions.can_manage_organization.name,
                OrganizationPermissions.can_manage_organization_users.name,
                OrganizationPermissions.can_manage_connected_role_organizations.name,
                OrganizationPermissions.can_list_organization_users.name,
            ],
        )
        self.role_org_manager_role = self.create_role_with_permissions(
            role_name="Test Role Org Manager",
            permissions=[
                OrganizationPermissions.can_view_organization.name,
                OrganizationPermissions.can_manage_connected_role_organizations.name,
                OrganizationPermissions.can_list_organization_users.name,
            ],
        )
        self.role_org_member_role = self.create_role_with_permissions(
            role_name="Test Role Org Member",
            permissions=[
                OrganizationPermissions.can_view_organization.name,
            ],
        )

        self.health_dept = self.create_organization(
            name="Health Department", org_type="role"
        )
        self.doctors_org = self.create_organization(name="Doctors", org_type="role")
        self.nurses_org = self.create_organization(name="Nurses", org_type="role")
        self.govt_org = self.create_organization(name="State Govt", org_type="govt")

    def get_managing_org_url(self, org_external_id):
        return reverse(
            "organization-managing-organization",
            kwargs={"external_id": str(org_external_id)},
        )

    # --- Add managing organization ---

    def test_add_managing_organization_as_superuser(self):
        self.client.force_authenticate(user=self.super_user)
        response = self.client.post(
            self.get_managing_org_url(self.doctors_org.external_id),
            {
                "organization": str(self.health_dept.external_id),
                "action": "add",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.doctors_org.refresh_from_db()
        self.assertIn(self.health_dept.id, self.doctors_org.managing_organizations)

    def test_add_managing_organization_as_role_org_admin(self):
        self.attach_role_organization_user(
            self.health_dept, self.user, self.role_org_admin_role
        )
        self.attach_role_organization_user(
            self.doctors_org, self.user, self.role_org_admin_role
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.get_managing_org_url(self.doctors_org.external_id),
            {
                "organization": str(self.health_dept.external_id),
                "action": "add",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.doctors_org.refresh_from_db()
        self.assertIn(self.health_dept.id, self.doctors_org.managing_organizations)

    def test_add_managing_organization_without_permission_on_managing_org(self):
        self.attach_role_organization_user(
            self.doctors_org, self.user, self.role_org_admin_role
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.get_managing_org_url(self.doctors_org.external_id),
            {
                "organization": str(self.health_dept.external_id),
                "action": "add",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_add_managing_organization_without_permission_on_target_org(self):
        self.attach_role_organization_user(
            self.health_dept, self.user, self.role_org_admin_role
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.get_managing_org_url(self.doctors_org.external_id),
            {
                "organization": str(self.health_dept.external_id),
                "action": "add",
            },
            format="json",
        )
        # User cannot see the target org, so gets 404
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_add_managing_organization_as_member_denied(self):
        self.attach_role_organization_user(
            self.health_dept, self.user, self.role_org_member_role
        )
        self.attach_role_organization_user(
            self.doctors_org, self.user, self.role_org_member_role
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.get_managing_org_url(self.doctors_org.external_id),
            {
                "organization": str(self.health_dept.external_id),
                "action": "add",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_add_managing_organization_rejects_non_role_orgs(self):
        self.client.force_authenticate(user=self.super_user)
        response = self.client.post(
            self.get_managing_org_url(self.doctors_org.external_id),
            {
                "organization": str(self.govt_org.external_id),
                "action": "add",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_managing_organization_rejects_non_role_target_org(self):
        self.client.force_authenticate(user=self.super_user)
        response = self.client.post(
            self.get_managing_org_url(self.govt_org.external_id),
            {
                "organization": str(self.health_dept.external_id),
                "action": "add",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_managing_organization_is_idempotent(self):
        self.client.force_authenticate(user=self.super_user)
        url = self.get_managing_org_url(self.doctors_org.external_id)
        data = {
            "organization": str(self.health_dept.external_id),
            "action": "add",
        }
        self.client.post(url, data, format="json")
        self.client.post(url, data, format="json")
        self.doctors_org.refresh_from_db()
        self.assertEqual(
            self.doctors_org.managing_organizations.count(self.health_dept.id), 1
        )

    def test_add_multiple_managing_organizations(self):
        other_dept = self.create_organization(name="Medical Council", org_type="role")
        self.client.force_authenticate(user=self.super_user)
        url = self.get_managing_org_url(self.doctors_org.external_id)
        self.client.post(
            url,
            {"organization": str(self.health_dept.external_id), "action": "add"},
            format="json",
        )
        self.client.post(
            url,
            {"organization": str(other_dept.external_id), "action": "add"},
            format="json",
        )
        self.doctors_org.refresh_from_db()
        self.assertIn(self.health_dept.id, self.doctors_org.managing_organizations)
        self.assertIn(other_dept.id, self.doctors_org.managing_organizations)

    # --- Remove managing organization ---

    def test_remove_managing_organization(self):
        self.doctors_org.managing_organizations = [self.health_dept.id]
        self.doctors_org.save(update_fields=["managing_organizations"])
        self.client.force_authenticate(user=self.super_user)
        response = self.client.post(
            self.get_managing_org_url(self.doctors_org.external_id),
            {
                "organization": str(self.health_dept.external_id),
                "action": "remove",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.doctors_org.refresh_from_db()
        self.assertNotIn(self.health_dept.id, self.doctors_org.managing_organizations)

    def test_remove_managing_organization_not_in_list(self):
        self.client.force_authenticate(user=self.super_user)
        response = self.client.post(
            self.get_managing_org_url(self.doctors_org.external_id),
            {
                "organization": str(self.health_dept.external_id),
                "action": "remove",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- Retrieve includes managing organizations ---

    def test_retrieve_organization_includes_managing_organizations(self):
        self.doctors_org.managing_organizations = [self.health_dept.id]
        self.doctors_org.save(update_fields=["managing_organizations"])
        self.client.force_authenticate(user=self.super_user)
        url = reverse(
            "organization-detail",
            kwargs={"external_id": str(self.doctors_org.external_id)},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        managing_orgs = response.data["managing_organizations"]
        self.assertEqual(len(managing_orgs), 1)
        self.assertEqual(managing_orgs[0]["id"], str(self.health_dept.external_id))

    def test_retrieve_organization_empty_managing_organizations(self):
        self.client.force_authenticate(user=self.super_user)
        url = reverse(
            "organization-detail",
            kwargs={"external_id": str(self.doctors_org.external_id)},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["managing_organizations"], [])


class ManagingOrganizationFilterTestCase(CareAPITestBase):
    """Tests for the get_managed_organizations filter."""

    def setUp(self):
        super().setUp()
        self.super_user = self.create_super_user()
        self.health_dept = self.create_organization(
            name="Health Department", org_type="role"
        )
        self.doctors_org = self.create_organization(
            name="Doctors",
            org_type="role",
            managing_organizations=[self.health_dept.id],
        )
        self.nurses_org = self.create_organization(
            name="Nurses",
            org_type="role",
            managing_organizations=[self.health_dept.id],
        )
        self.unmanaged_org = self.create_organization(name="Unmanaged", org_type="role")
        self.url = reverse("organization-list")

    def test_filter_managed_organizations(self):
        self.client.force_authenticate(user=self.super_user)
        response = self.client.get(
            self.url,
            {"get_managed_organizations": str(self.health_dept.external_id)},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_ids = [r["id"] for r in response.data["results"]]
        self.assertIn(str(self.doctors_org.external_id), result_ids)
        self.assertIn(str(self.nurses_org.external_id), result_ids)
        self.assertNotIn(str(self.unmanaged_org.external_id), result_ids)

    def test_filter_managed_organizations_no_results(self):
        self.client.force_authenticate(user=self.super_user)
        response = self.client.get(
            self.url,
            {"get_managed_organizations": str(self.unmanaged_org.external_id)},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)


class ManagingOrganizationAuthorizationTestCase(CareAPITestBase):
    """Tests for managing org authorization: users in a managing org can manage users in managed orgs."""

    def setUp(self):
        super().setUp()
        self.super_user = self.create_super_user()
        self.admin_user = self.create_user()
        self.manager_user = self.create_user()
        self.member_user = self.create_user()
        self.target_user = self.create_user()

        self.role_org_admin_role = self.create_role_with_permissions(
            role_name="Test Role Org Admin",
            permissions=[
                OrganizationPermissions.can_view_organization.name,
                OrganizationPermissions.can_manage_organization.name,
                OrganizationPermissions.can_manage_organization_users.name,
                OrganizationPermissions.can_manage_connected_role_organizations.name,
                OrganizationPermissions.can_list_organization_users.name,
            ],
        )
        self.role_org_manager_role = self.create_role_with_permissions(
            role_name="Test Role Org Manager",
            permissions=[
                OrganizationPermissions.can_view_organization.name,
                OrganizationPermissions.can_manage_connected_role_organizations.name,
                OrganizationPermissions.can_list_organization_users.name,
            ],
        )
        self.role_org_member_role = self.create_role_with_permissions(
            role_name="Test Role Org Member",
            permissions=[
                OrganizationPermissions.can_view_organization.name,
            ],
        )

        self.health_dept = self.create_organization(
            name="Health Department", org_type="role"
        )
        self.doctors_org = self.create_organization(
            name="Doctors",
            org_type="role",
            managing_organizations=[self.health_dept.id],
        )

        # Assign users to Health Dept
        self.attach_role_organization_user(
            self.health_dept, self.admin_user, self.role_org_admin_role
        )
        self.attach_role_organization_user(
            self.health_dept, self.manager_user, self.role_org_manager_role
        )
        self.attach_role_organization_user(
            self.health_dept, self.member_user, self.role_org_member_role
        )

    def get_org_users_url(self, org_external_id):
        return reverse(
            "organization-users-list",
            kwargs={"organization_external_id": str(org_external_id)},
        )

    def test_admin_in_managing_org_can_add_user_to_managed_org(self):
        """Role Org Admin in Health Dept can add users to Doctors org."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            self.get_org_users_url(self.doctors_org.external_id),
            {
                "user": str(self.target_user.external_id),
                "role": str(self.role_org_member_role.external_id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_manager_in_managing_org_can_add_user_to_managed_org(self):
        """Role Org Manager in Health Dept can add users to Doctors org."""
        self.client.force_authenticate(user=self.manager_user)
        response = self.client.post(
            self.get_org_users_url(self.doctors_org.external_id),
            {
                "user": str(self.target_user.external_id),
                "role": str(self.role_org_member_role.external_id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_member_in_managing_org_cannot_add_user_to_managed_org(self):
        """Role Org Member in Health Dept cannot add users to Doctors org."""
        self.client.force_authenticate(user=self.member_user)
        response = self.client.post(
            self.get_org_users_url(self.doctors_org.external_id),
            {
                "user": str(self.target_user.external_id),
                "role": str(self.role_org_member_role.external_id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_in_unconnected_org_cannot_add_user_to_managed_org(self):
        """User in a different org (not a managing org) cannot add to Doctors org."""
        unconnected = self.create_organization(name="Unconnected", org_type="role")
        outsider = self.create_user()
        self.attach_role_organization_user(
            unconnected, outsider, self.role_org_admin_role
        )
        self.client.force_authenticate(user=outsider)
        response = self.client.post(
            self.get_org_users_url(self.doctors_org.external_id),
            {
                "user": str(self.target_user.external_id),
                "role": str(self.role_org_member_role.external_id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_removing_managing_org_revokes_access(self):
        """After removing Health Dept as managing org, its admin can no longer manage Doctors."""
        self.doctors_org.managing_organizations = []
        self.doctors_org.save(update_fields=["managing_organizations"])
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            self.get_org_users_url(self.doctors_org.external_id),
            {
                "user": str(self.target_user.external_id),
                "role": str(self.role_org_member_role.external_id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RoleContextFilterTestCase(CareAPITestBase):
    """Tests for the role context filter on the Roles API."""

    def setUp(self):
        super().setUp()
        self.super_user = self.create_super_user()
        self.facility_role = self.create_role(
            name="Test Facility Role",
            contexts=[RoleContext.FACILITY.value],
        )
        self.role_org_role = self.create_role(
            name="Test Role Org Role",
            contexts=[RoleContext.ROLE_ORG.value],
        )
        self.multi_context_role = self.create_role(
            name="Test Multi Context Role",
            contexts=[RoleContext.FACILITY.value, RoleContext.GOVT_ORG.value],
        )
        self.url = reverse("role-list")

    def test_filter_roles_by_facility_context(self):
        self.client.force_authenticate(user=self.super_user)
        response = self.client.get(self.url, {"context": RoleContext.FACILITY.value})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_names = [r["name"] for r in response.data["results"]]
        self.assertIn("Test Facility Role", result_names)
        self.assertIn("Test Multi Context Role", result_names)
        self.assertNotIn("Test Role Org Role", result_names)

    def test_filter_roles_by_role_org_context(self):
        self.client.force_authenticate(user=self.super_user)
        response = self.client.get(self.url, {"context": RoleContext.ROLE_ORG.value})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_names = [r["name"] for r in response.data["results"]]
        self.assertIn("Test Role Org Role", result_names)
        self.assertNotIn("Test Facility Role", result_names)

    def test_filter_roles_by_govt_org_context(self):
        self.client.force_authenticate(user=self.super_user)
        response = self.client.get(self.url, {"context": RoleContext.GOVT_ORG.value})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_names = [r["name"] for r in response.data["results"]]
        self.assertIn("Test Multi Context Role", result_names)
        self.assertNotIn("Test Role Org Role", result_names)

    def test_no_context_filter_returns_all(self):
        self.client.force_authenticate(user=self.super_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_names = [r["name"] for r in response.data["results"]]
        self.assertIn("Test Facility Role", result_names)
        self.assertIn("Test Role Org Role", result_names)
        self.assertIn("Test Multi Context Role", result_names)


class CachedRoleOrgsTestCase(CareAPITestBase):
    """Tests for cached_role_orgs on user serialization and cache invalidation."""

    def setUp(self):
        super().setUp()
        self.super_user = self.create_super_user()
        self.user = self.create_user()
        self.role_org_member_role = self.create_role_with_permissions(
            role_name="Test Role Org Member",
            permissions=[
                OrganizationPermissions.can_view_organization.name,
            ],
        )
        self.doctors_org = self.create_organization(name="Doctors", org_type="role")

    def test_cached_role_orgs_populated_on_first_access(self):
        self.attach_role_organization_user(
            self.doctors_org, self.user, self.role_org_member_role
        )
        self.user.refresh_from_db()
        self.assertIsNone(self.user.cached_role_orgs)
        data = self.user.get_cached_role_orgs()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["organization"]["name"], "Doctors")
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.cached_role_orgs)

    def test_cached_role_orgs_invalidated_on_org_user_save(self):
        self.attach_role_organization_user(
            self.doctors_org, self.user, self.role_org_member_role
        )
        # Populate cache
        self.user.get_cached_role_orgs()
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.cached_role_orgs)

        # Add to another role org — triggers save() which invalidates cache
        other_org = self.create_organization(name="Nurses", org_type="role")
        self.attach_role_organization_user(
            other_org, self.user, self.role_org_member_role
        )
        self.user.refresh_from_db()
        self.assertIsNone(self.user.cached_role_orgs)

    def test_cached_role_orgs_not_invalidated_for_non_role_orgs(self):
        # Assign user to a role org and populate cache
        self.attach_role_organization_user(
            self.doctors_org, self.user, self.role_org_member_role
        )
        self.user.get_cached_role_orgs()
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.cached_role_orgs)

        # Add user to a govt org — should NOT invalidate role org cache
        admin_role = self.create_role_with_permissions(
            role_name="Test Govt Admin",
            permissions=[OrganizationPermissions.can_view_organization.name],
        )
        govt_org = self.create_organization(name="Govt Org", org_type="govt")
        self.attach_role_organization_user(govt_org, self.user, admin_role)
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.cached_role_orgs)

    def test_user_serialization_includes_role_orgs(self):
        self.attach_role_organization_user(
            self.doctors_org, self.user, self.role_org_member_role
        )
        self.client.force_authenticate(user=self.super_user)
        response = self.client.get(
            reverse("users-detail", kwargs={"username": self.user.username})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("role_orgs", response.data)

    def test_user_serialization_empty_role_orgs(self):
        self.client.force_authenticate(user=self.super_user)
        response = self.client.get(
            reverse("users-detail", kwargs={"username": self.user.username})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("role_orgs", response.data)


class UserCreationWithRoleOrgsTestCase(CareAPITestBase):
    """Tests for user creation with the new role_orgs field."""

    def setUp(self):
        super().setUp()
        self.super_user = self.create_super_user()
        self.user = self.create_user()
        self.admin_role = self.create_role_with_permissions(
            role_name="Test Admin",
            permissions=[
                OrganizationPermissions.can_view_organization.name,
                OrganizationPermissions.can_manage_organization.name,
                OrganizationPermissions.can_manage_organization_users.name,
                OrganizationPermissions.can_list_organization_users.name,
                UserPermissions.can_create_user.name,
            ],
        )
        self.role_org_admin_role = self.create_role_with_permissions(
            role_name="Test Role Org Admin",
            permissions=[
                OrganizationPermissions.can_view_organization.name,
                OrganizationPermissions.can_manage_organization.name,
                OrganizationPermissions.can_manage_organization_users.name,
                OrganizationPermissions.can_manage_connected_role_organizations.name,
                OrganizationPermissions.can_list_organization_users.name,
            ],
        )
        self.role_org_member_role = self.create_role_with_permissions(
            role_name="Test Role Org Member",
            permissions=[
                OrganizationPermissions.can_view_organization.name,
            ],
        )
        self.organization = self.create_organization(
            name="Test Govt Org", org_type="govt"
        )
        self.doctors_org = self.create_organization(name="Doctors", org_type="role")
        self.url = reverse("users-list")

    def _user_data(self, **overrides):
        data = {
            "username": f"testuser{self.fake.random_int()}",
            "first_name": "Test",
            "last_name": "User",
            "email": f"{self.fake.random_int()}test@example.com",
            "password": "ComplexP@ssw0rd",
            "gender": "non_binary",
            "geo_organization": str(self.organization.external_id),
            "phone_number": f"{self.fake.random_int(min=1000000000, max=9999999999)}",
            "role_orgs": [],
        }
        data.update(overrides)
        return data

    def test_create_user_with_role_orgs_as_superuser(self):
        self.client.force_authenticate(user=self.super_user)
        data = self._user_data(
            role_orgs=[
                {
                    "organization": str(self.doctors_org.external_id),
                    "role": str(self.role_org_member_role.external_id),
                }
            ]
        )
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        created_user = OrganizationUser.objects.filter(
            user__username=data["username"],
            organization=self.doctors_org,
        )
        self.assertTrue(created_user.exists())

    def test_create_user_with_empty_role_orgs(self):
        self.client.force_authenticate(user=self.super_user)
        data = self._user_data(role_orgs=[])
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_user_without_role_orgs_field_fails(self):
        self.client.force_authenticate(user=self.super_user)
        data = self._user_data()
        del data["role_orgs"]
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_user_with_role_orgs_requires_permission(self):
        """User without permission on the role org cannot assign it during creation."""
        self.attach_role_organization_user(
            self.organization, self.user, self.admin_role
        )
        self.client.force_authenticate(user=self.user)
        data = self._user_data(
            role_orgs=[
                {
                    "organization": str(self.doctors_org.external_id),
                    "role": str(self.role_org_member_role.external_id),
                }
            ]
        )
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_user_with_non_role_org_fails(self):
        self.client.force_authenticate(user=self.super_user)
        data = self._user_data(
            role_orgs=[
                {
                    "organization": str(self.organization.external_id),
                    "role": str(self.admin_role.external_id),
                }
            ]
        )
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_user_with_role_orgs_authorized_via_managing_org(self):
        """User who is admin of managing org can assign roles in managed org during user creation."""
        health_dept = self.create_organization(
            name="Health Department", org_type="role"
        )
        self.doctors_org.managing_organizations = [health_dept.id]
        self.doctors_org.save(update_fields=["managing_organizations"])

        # Give user admin in health dept + permission to create users
        self.attach_role_organization_user(
            health_dept, self.user, self.role_org_admin_role
        )
        self.attach_role_organization_user(
            self.organization, self.user, self.admin_role
        )

        self.client.force_authenticate(user=self.user)
        data = self._user_data(
            role_orgs=[
                {
                    "organization": str(self.doctors_org.external_id),
                    "role": str(self.role_org_member_role.external_id),
                }
            ]
        )
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            OrganizationUser.objects.filter(
                user__username=data["username"],
                organization=self.doctors_org,
            ).exists()
        )
