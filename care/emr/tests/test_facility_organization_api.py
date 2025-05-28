from django.urls import reverse

from care.emr.models.organization import FacilityOrganizationUser
from care.security.permissions.facility_organization import (
    FacilityOrganizationPermissions,
)
from care.security.roles.role import FACILITY_ADMIN_ROLE
from care.utils.tests.base import CareAPITestBase


class FacilityOrganizationUserApiTestCases(CareAPITestBase):
    def setUp(self):
        self.facility_admin_role = self.create_role_with_permissions(
            role_name=FACILITY_ADMIN_ROLE.name,
            permissions=[
                FacilityOrganizationPermissions.can_view_facility_organization.name,
                FacilityOrganizationPermissions.can_list_facility_organization_users.name,
                FacilityOrganizationPermissions.can_manage_facility_organization_users.name,
            ],
        )

        self.super_user = self.create_super_user()
        self.facility = self.create_facility(user=self.super_user)
        self.facility_root_organization = self.facility.default_internal_organization

    def test_user_can_update_role_of_user_with_subset_roles(self):
        """
        Test that a user can update the role of another user with a subset of roles.
        """

        user = self.create_user()
        self.attach_role_facility_organization_user(
            self.facility_root_organization, user, self.facility_admin_role
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
        self.attach_role_facility_organization_user(
            self.facility_root_organization, user, self.facility_admin_role
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

    def test_change_role_when_user_is_only_admin_in_organization(self):
        """
        Test that a user that is the only facility admin in the organization cannot update their own role.
        """

        user = self.create_user()
        facility = self.create_facility(user=user)
        facility_root_organization = facility.default_internal_organization

        org_role_obj = FacilityOrganizationUser.objects.get(
            organization=facility_root_organization,
            user=user,
        )

        role_to_update = self.create_role_with_permissions(
            permissions=[
                FacilityOrganizationPermissions.can_view_facility_organization.name,
            ],
        )

        url = reverse(
            "facility-organization-users-detail",
            kwargs={
                "facility_external_id": facility.external_id,
                "facility_organizations_external_id": facility_root_organization.external_id,
                "external_id": org_role_obj.external_id,
            },
        )

        self.client.force_authenticate(user)

        response = self.client.put(url, data={"role": role_to_update.external_id})
        self.assertContains(
            response,
            "Cannot change the role of the last admin user in the root organization",
            status_code=400,
        )

    def test_change_role_when_user_is_not_only_admin_in_organization(self):
        """
        Test that a user that is not the only facility admin in the organization can update their own role.
        """

        user = self.create_user()
        facility = self.create_facility(user=user)
        facility_root_organization = facility.default_internal_organization

        other_user = self.create_user()
        self.attach_role_facility_organization_user(
            facility_root_organization, other_user, self.facility_admin_role
        )

        org_role_obj = FacilityOrganizationUser.objects.get(
            organization=facility_root_organization,
            user=user,
        )

        role_to_update = self.create_role_with_permissions(
            permissions=[
                FacilityOrganizationPermissions.can_view_facility_organization.name,
            ],
        )

        url = reverse(
            "facility-organization-users-detail",
            kwargs={
                "facility_external_id": facility.external_id,
                "facility_organizations_external_id": facility_root_organization.external_id,
                "external_id": org_role_obj.external_id,
            },
        )

        self.client.force_authenticate(user)

        response = self.client.put(url, data={"role": role_to_update.external_id})
        self.assertEqual(response.status_code, 200, response.data)
