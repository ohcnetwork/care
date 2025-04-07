from django.urls import reverse

from care.security.permissions.facility_organization import (
    FacilityOrganizationPermissions,
)
from care.utils.tests.base import CareAPITestBase


class FacilityOrgainzationUserApiTestCases(CareAPITestBase):
    def setUp(self):
        self.super_user = self.create_super_user()
        self.facility = self.create_facility(user=self.super_user)
        self.facility_root_organization = self.facility.default_internal_organization

    def test_user_can_update_role_of_user_with_subset_roles(self):
        """
        Test that a user can update the role of another user with a subset of roles.
        """

        user = self.create_user()
        role = self.create_role_with_permissions(
            permissions=[
                FacilityOrganizationPermissions.can_view_facility_organization.name,
                FacilityOrganizationPermissions.can_list_facility_organization_users.name,
                FacilityOrganizationPermissions.can_manage_facility_organization_users.name,
            ]
        )
        self.attach_role_facility_organization_user(
            self.facility_root_organization, user, role
        )

        user_with_fewer_permissions = self.create_user()
        role_with_fewer_permissions = self.create_role_with_permissions(
            permissions=[
                FacilityOrganizationPermissions.can_view_facility_organization.name,
                FacilityOrganizationPermissions.can_list_facility_organization_users.name,
            ]
        )
        org_role_obj = self.attach_role_facility_organization_user(
            self.facility_root_organization,
            user_with_fewer_permissions,
            role_with_fewer_permissions,
        )

        role_to_update = self.create_role_with_permissions(
            permissions=[
                FacilityOrganizationPermissions.can_view_facility_organization.name,
            ]
        )

        url = reverse(
            "facility-organization-users-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "facility_organizations_external_id": self.facility_root_organization.external_id,
                "external_id": org_role_obj.external_id,
            },
        )

        self.client.force_authenticate(user)

        response = self.client.put(url, data={"role": role_to_update.external_id})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            response.data["role"]["id"],
            str(role_to_update.external_id),
            response.data,
        )

    def test_user_cannot_update_role_of_user_with_non_subset_roles(self):
        """
        Test that a user cannot update the role of another user with non-subset roles.
        """

        user = self.create_user()
        role = self.create_role_with_permissions(
            permissions=[
                FacilityOrganizationPermissions.can_view_facility_organization.name,
                FacilityOrganizationPermissions.can_list_facility_organization_users.name,
                FacilityOrganizationPermissions.can_manage_facility_organization_users.name,
            ]
        )
        self.attach_role_facility_organization_user(
            self.facility_root_organization, user, role
        )

        user_with_fewer_permissions = self.create_user()
        role_with_fewer_permissions = self.create_role_with_permissions(
            permissions=[
                FacilityOrganizationPermissions.can_view_facility_organization.name,
                FacilityOrganizationPermissions.can_list_facility_organization_users.name,
            ]
        )
        org_role_obj = self.attach_role_facility_organization_user(
            self.facility_root_organization,
            user_with_fewer_permissions,
            role_with_fewer_permissions,
        )

        role_to_update = self.create_role_with_permissions(
            permissions=[
                FacilityOrganizationPermissions.can_view_facility_organization.name,
                FacilityOrganizationPermissions.can_delete_facility_organization.name,
            ]
        )

        url = reverse(
            "facility-organization-users-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "facility_organizations_external_id": self.facility_root_organization.external_id,
                "external_id": org_role_obj.external_id,
            },
        )

        self.client.force_authenticate(user)

        response = self.client.put(url, data={"role": role_to_update.external_id})
        self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(
            response.data["detail"],
            "User does not have permission for this action",
            response.data,
        )

    def test_user_can_update_own_role_if_only_user_in_org(self):
        """
        Test that a user can update its own role if it is the only user in the organization.
        """

        user = self.create_user()
        role = self.create_role_with_permissions(
            permissions=[
                FacilityOrganizationPermissions.can_view_facility_organization.name,
                FacilityOrganizationPermissions.can_list_facility_organization_users.name,
                FacilityOrganizationPermissions.can_manage_facility_organization_users.name,
            ]
        )
        org_role_obj = self.attach_role_facility_organization_user(
            self.facility_root_organization, user, role
        )

        role_to_update = self.create_role_with_permissions(
            permissions=[
                FacilityOrganizationPermissions.can_view_facility_organization.name,
                FacilityOrganizationPermissions.can_list_facility_organization_users.name,
                FacilityOrganizationPermissions.can_manage_facility_organization_users.name,
                FacilityOrganizationPermissions.can_delete_facility_organization.name,
            ]
        )

        url = reverse(
            "facility-organization-users-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "facility_organizations_external_id": self.facility_root_organization.external_id,
                "external_id": org_role_obj.external_id,
            },
        )

        self.client.force_authenticate(user)

        response = self.client.put(url, data={"role": role_to_update.external_id})
        self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(
            response.data["detail"],
            "User does not have permission for this action",
            response.data,
        )
