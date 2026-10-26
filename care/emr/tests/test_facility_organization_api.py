import uuid

from django.conf import settings
from django.test.utils import override_settings
from django.urls import reverse
from model_bakery import baker

from care.emr.models.device import Device
from care.emr.models.location import FacilityLocation, FacilityLocationOrganization
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
        self.child_organization = self.create_facility_organization(
            self.facility,
            parent=self.facility_root_organization,
            org_type="dept",
            name="Child",
        )
        self.viewer_role = self.create_role_with_permissions(
            permissions=[
                FacilityOrganizationPermissions.can_view_facility_organization.name,
                FacilityOrganizationPermissions.can_list_facility_organization_users.name,
            ]
        )
        self.basic_role = self.create_role_with_permissions(
            permissions=[
                FacilityOrganizationPermissions.can_view_facility_organization.name,
            ]
        )

    def get_list_url(self, organization=None):
        return reverse(
            "facility-organization-users-list",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "facility_organizations_external_id": (
                    organization or self.facility_root_organization
                ).external_id,
            },
        )

    def get_detail_url(self, org_user, organization=None):
        return reverse(
            "facility-organization-users-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "facility_organizations_external_id": (
                    organization or self.facility_root_organization
                ).external_id,
                "external_id": org_user.external_id,
            },
        )

    def list_ids(self, response):
        return {result["id"] for result in response.data["results"]}

    def create_admin(self, organization=None):
        user = self.create_user()
        self.attach_role_facility_organization_user(
            organization or self.facility_root_organization,
            user,
            self.facility_admin_role,
        )
        return user

    def add_member(self, organization=None, role=None, **user_kwargs):
        return self.attach_role_facility_organization_user(
            organization or self.facility_root_organization,
            self.create_user(**user_kwargs),
            role or self.basic_role,
        )

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

    # List
    def test_list_users_without_authentication(self):
        """
        Test that an unauthenticated request cannot list organization users.
        """
        response = self.client.get(self.get_list_url())
        self.assertEqual(response.status_code, 403, response.data)

    def test_list_users_as_superuser(self):
        """
        Test that a superuser can list the users of any facility organization.
        """
        member = self.add_member(self.child_organization)
        self.client.force_authenticate(self.super_user)
        response = self.client.get(self.get_list_url(self.child_organization))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.list_ids(response), {str(member.external_id)})

    def test_list_users_as_user_with_permission(self):
        """
        Test that a user with the list users permission can list organization users.
        """
        admin = self.create_admin()
        member = self.add_member()
        self.client.force_authenticate(admin)
        response = self.client.get(self.get_list_url())
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(
            {str(member.external_id)}.issubset(self.list_ids(response)),
        )

    def test_list_users_as_user_without_permission(self):
        """
        Test that a user without the list users permission cannot list organization users.
        """
        member = self.add_member()
        self.client.force_authenticate(member.user)
        response = self.client.get(self.get_list_url())
        self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(
            response.data["detail"],
            "User does not have the required permissions to list users",
        )

    def test_list_users_as_user_not_in_facility(self):
        """
        Test that a user who is not part of the facility cannot list organization users.
        """
        self.client.force_authenticate(self.create_user())
        response = self.client.get(self.get_list_url())
        self.assertEqual(response.status_code, 403, response.data)

    def test_list_users_only_returns_users_of_the_organization(self):
        """
        Test that listing returns only the users attached to the requested organization.
        """
        member = self.add_member(self.child_organization)
        self.add_member(self.facility_root_organization)
        self.client.force_authenticate(self.super_user)
        response = self.client.get(self.get_list_url(self.child_organization))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.list_ids(response), {str(member.external_id)})

    def test_list_users_excludes_deleted(self):
        """
        Test that soft-deleted organization users are not listed.
        """
        member = self.add_member(self.child_organization)
        member.deleted = True
        member.save(update_fields=["deleted"])
        self.client.force_authenticate(self.super_user)
        response = self.client.get(self.get_list_url(self.child_organization))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 0)

    def test_list_users_with_invalid_organization(self):
        """
        Test that listing users of a non-existent organization returns 404.
        """
        self.client.force_authenticate(self.super_user)
        url = reverse(
            "facility-organization-users-list",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "facility_organizations_external_id": uuid.uuid4(),
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404, response.data)

    def test_list_users_excludes_service_accounts_by_default(self):
        """
        Test that service accounts are hidden from the list unless explicitly requested.
        """
        self.add_member(self.child_organization, is_service_account=True)
        regular = self.add_member(self.child_organization)
        self.client.force_authenticate(self.super_user)
        response = self.client.get(self.get_list_url(self.child_organization))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.list_ids(response), {str(regular.external_id)})

    def test_list_users_filter_service_accounts(self):
        """
        Test that the is_service_account filter returns only service accounts.
        """
        service_account = self.add_member(
            self.child_organization, is_service_account=True
        )
        self.add_member(self.child_organization)
        self.client.force_authenticate(self.super_user)
        response = self.client.get(
            self.get_list_url(self.child_organization), {"is_service_account": "true"}
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.list_ids(response), {str(service_account.external_id)})

    def test_list_users_search(self):
        """
        Test that users can be searched by their name.
        """
        match = self.add_member(
            self.child_organization, first_name="Zebulon", last_name="Quimby"
        )
        self.add_member(self.child_organization, first_name="Other", last_name="Person")
        self.client.force_authenticate(self.super_user)
        response = self.client.get(
            self.get_list_url(self.child_organization), {"search_text": "zebu"}
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.list_ids(response), {str(match.external_id)})

    def test_list_users_pagination(self):
        """
        Test that the user list is paginated using the limit parameter.
        """
        for _ in range(3):
            self.add_member(self.child_organization)
        self.client.force_authenticate(self.super_user)
        response = self.client.get(
            self.get_list_url(self.child_organization), {"limit": 2}
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(len(response.data["results"]), 2)

    # Retrieve
    def test_retrieve_user_as_user_with_permission(self):
        """
        Test that a user with the list users permission can retrieve an organization user.
        """
        admin = self.create_admin()
        member = self.add_member()
        self.client.force_authenticate(admin)
        response = self.client.get(self.get_detail_url(member))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["id"], str(member.external_id))
        self.assertEqual(response.data["user"]["id"], str(member.user.external_id))
        self.assertEqual(response.data["role"]["id"], str(self.basic_role.external_id))

    def test_retrieve_user_as_user_without_permission(self):
        """
        Test that a user without the list users permission cannot retrieve an organization user.
        """
        member = self.add_member()
        self.client.force_authenticate(self.create_user())
        response = self.client.get(self.get_detail_url(member))
        self.assertEqual(response.status_code, 403, response.data)

    def test_retrieve_user_from_another_organization(self):
        """
        Test that a user attached to a different organization cannot be retrieved through this one.
        """
        member = self.add_member(self.child_organization)
        self.client.force_authenticate(self.super_user)
        response = self.client.get(self.get_detail_url(member))
        self.assertEqual(response.status_code, 404, response.data)

    def test_retrieve_user_with_invalid_id(self):
        """
        Test that retrieving a non-existent organization user returns 404.
        """
        self.client.force_authenticate(self.super_user)
        member = self.add_member()
        member.external_id = uuid.uuid4()
        response = self.client.get(self.get_detail_url(member))
        self.assertEqual(response.status_code, 404, response.data)

    # Create
    def test_add_user_as_superuser(self):
        """
        Test that a superuser can add a user to an organization.
        """
        user = self.create_user()
        self.client.force_authenticate(self.super_user)
        response = self.client.post(
            self.get_list_url(self.child_organization),
            {"user": user.external_id, "role": self.basic_role.external_id},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(
            FacilityOrganizationUser.objects.filter(
                organization=self.child_organization,
                user=user,
                role=self.basic_role,
            ).exists()
        )

    def test_add_user_as_user_with_permission(self):
        """
        Test that a user with the manage users permission can add a user with a subset role.
        """
        admin = self.create_admin()
        user = self.create_user()
        self.client.force_authenticate(admin)
        response = self.client.post(
            self.get_list_url(self.child_organization),
            {"user": user.external_id, "role": self.viewer_role.external_id},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["user"]["id"], str(user.external_id))
        self.assertEqual(response.data["role"]["id"], str(self.viewer_role.external_id))

    def test_add_user_as_user_without_permission(self):
        """
        Test that a user without the manage users permission cannot add users.
        """
        actor = self.add_member(role=self.viewer_role).user
        self.client.force_authenticate(actor)
        response = self.client.post(
            self.get_list_url(),
            {
                "user": self.create_user().external_id,
                "role": self.basic_role.external_id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(
            response.data["detail"], "User does not have permission for this action"
        )

    def test_add_user_with_role_exceeding_own_permissions(self):
        """
        Test that a user cannot add someone with a role that has permissions they do not have.
        """
        higher_role = self.create_role_with_permissions(
            permissions=[
                FacilityOrganizationPermissions.can_view_facility_organization.name,
                FacilityOrganizationPermissions.can_delete_facility_organization.name,
            ]
        )
        admin = self.create_admin()
        self.client.force_authenticate(admin)
        response = self.client.post(
            self.get_list_url(),
            {
                "user": self.create_user().external_id,
                "role": higher_role.external_id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403, response.data)

    def test_add_user_with_permission_only_on_child_organization(self):
        """
        Test that manage permission on a child organization does not allow adding users to its parent.
        """
        admin = self.create_admin(self.child_organization)
        self.client.force_authenticate(admin)
        response = self.client.post(
            self.get_list_url(),
            {
                "user": self.create_user().external_id,
                "role": self.basic_role.external_id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403, response.data)

    def test_add_user_with_permission_on_parent_organization(self):
        """
        Test that manage permission on a parent organization allows adding users to its child.
        """
        admin = self.create_admin()
        self.client.force_authenticate(admin)
        response = self.client.post(
            self.get_list_url(self.child_organization),
            {
                "user": self.create_user().external_id,
                "role": self.basic_role.external_id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)

    def test_add_user_without_authentication(self):
        """
        Test that an unauthenticated request cannot add a user to an organization.
        """
        response = self.client.post(
            self.get_list_url(),
            {
                "user": self.create_user().external_id,
                "role": self.basic_role.external_id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403, response.data)

    def test_add_user_already_in_organization(self):
        """
        Test that a user cannot be added to an organization they already belong to.
        """
        member = self.add_member(self.child_organization)
        self.client.force_authenticate(self.super_user)
        response = self.client.post(
            self.get_list_url(self.child_organization),
            {"user": member.user.external_id, "role": self.basic_role.external_id},
            format="json",
        )
        self.assertContains(
            response, "User association already exists", status_code=400
        )

    def test_add_user_already_in_parent_organization(self):
        """
        Test that a user cannot be added to an organization if already linked to one of its parents.
        """
        member = self.add_member()
        self.client.force_authenticate(self.super_user)
        response = self.client.post(
            self.get_list_url(self.child_organization),
            {"user": member.user.external_id, "role": self.basic_role.external_id},
            format="json",
        )
        self.assertContains(
            response, "User is already linked to a parent organization", status_code=400
        )

    def test_add_user_already_in_child_organization(self):
        """
        Test that a user cannot be added to an organization if already linked to one of its children.
        """
        member = self.add_member(self.child_organization)
        self.client.force_authenticate(self.super_user)
        response = self.client.post(
            self.get_list_url(),
            {"user": member.user.external_id, "role": self.basic_role.external_id},
            format="json",
        )
        self.assertContains(
            response, "User has association to some child organization", status_code=400
        )

    def test_add_user_already_in_a_sibling_organization(self):
        """
        Test that a user already linked to a sibling organization can still be added.
        """
        sibling = self.create_facility_organization(
            self.facility,
            parent=self.facility_root_organization,
            org_type="dept",
            name="Sibling",
        )
        member = self.add_member(sibling)
        self.client.force_authenticate(self.super_user)
        response = self.client.post(
            self.get_list_url(self.child_organization),
            {"user": member.user.external_id, "role": self.basic_role.external_id},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)

    def test_add_user_with_invalid_user(self):
        """
        Test that adding a non-existent user fails validation.
        """
        self.client.force_authenticate(self.super_user)
        response = self.client.post(
            self.get_list_url(self.child_organization),
            {"user": uuid.uuid4(), "role": self.basic_role.external_id},
            format="json",
        )
        self.assertContains(response, "User does not exist", status_code=400)

    def test_add_user_with_invalid_role(self):
        """
        Test that adding a user with a non-existent role fails validation.
        """
        self.client.force_authenticate(self.super_user)
        response = self.client.post(
            self.get_list_url(self.child_organization),
            {"user": self.create_user().external_id, "role": uuid.uuid4()},
            format="json",
        )
        self.assertContains(response, "Role does not exist", status_code=400)

    def test_add_user_without_required_fields(self):
        """
        Test that adding a user without the user and role fields fails validation.
        """
        self.client.force_authenticate(self.super_user)
        response = self.client.post(
            self.get_list_url(self.child_organization), {}, format="json"
        )
        self.assertEqual(response.status_code, 400, response.data)

    def test_add_user_to_invalid_organization(self):
        """
        Test that adding a user to a non-existent organization returns 404.
        """
        self.client.force_authenticate(self.super_user)
        url = reverse(
            "facility-organization-users-list",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "facility_organizations_external_id": uuid.uuid4(),
            },
        )
        response = self.client.post(
            url,
            {
                "user": self.create_user().external_id,
                "role": self.basic_role.external_id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 404, response.data)

    # Update
    def test_update_user_role_as_superuser(self):
        """
        Test that a superuser can change the role of an organization user.
        """
        member = self.add_member(self.child_organization)
        self.client.force_authenticate(self.super_user)
        response = self.client.put(
            self.get_detail_url(member, self.child_organization),
            {"role": self.viewer_role.external_id},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        member.refresh_from_db()
        self.assertEqual(member.role, self.viewer_role)

    def test_update_user_role_as_user_without_permission(self):
        """
        Test that a user without the manage users permission cannot change a user's role.
        """
        actor = self.add_member(role=self.viewer_role).user
        member = self.add_member(self.child_organization)
        self.client.force_authenticate(actor)
        response = self.client.put(
            self.get_detail_url(member, self.child_organization),
            {"role": self.basic_role.external_id},
            format="json",
        )
        self.assertEqual(response.status_code, 403, response.data)
        member.refresh_from_db()
        self.assertEqual(member.role, self.basic_role)

    def test_update_user_role_with_invalid_role(self):
        """
        Test that updating a user's role to a non-existent role fails validation.
        """
        member = self.add_member(self.child_organization)
        self.client.force_authenticate(self.super_user)
        response = self.client.put(
            self.get_detail_url(member, self.child_organization),
            {"role": uuid.uuid4()},
            format="json",
        )
        self.assertContains(response, "Role does not exist", status_code=400)

    def test_update_user_role_without_role(self):
        """
        Test that updating a user without providing a role fails validation.
        """
        member = self.add_member(self.child_organization)
        self.client.force_authenticate(self.super_user)
        response = self.client.put(
            self.get_detail_url(member, self.child_organization), {}, format="json"
        )
        self.assertEqual(response.status_code, 400, response.data)

    def test_update_user_role_does_not_change_user(self):
        """
        Test that an update only changes the role and ignores an attempt to change the user.
        """
        member = self.add_member(self.child_organization)
        original_user = member.user
        self.client.force_authenticate(self.super_user)
        response = self.client.put(
            self.get_detail_url(member, self.child_organization),
            {
                "role": self.viewer_role.external_id,
                "user": self.create_user().external_id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        member.refresh_from_db()
        self.assertEqual(member.user, original_user)

    def test_update_user_role_without_authentication(self):
        """
        Test that an unauthenticated request cannot change a user's role.
        """
        member = self.add_member(self.child_organization)
        response = self.client.put(
            self.get_detail_url(member, self.child_organization),
            {"role": self.viewer_role.external_id},
            format="json",
        )
        self.assertEqual(response.status_code, 403, response.data)

    # Destroy
    def test_remove_user_as_superuser(self):
        """
        Test that a superuser can remove a user from an organization.
        """
        member = self.add_member(self.child_organization)
        self.client.force_authenticate(self.super_user)
        response = self.client.delete(
            self.get_detail_url(member, self.child_organization)
        )
        self.assertEqual(response.status_code, 204, response.data)
        member.refresh_from_db()
        self.assertTrue(member.deleted)

    def test_remove_user_as_user_with_permission(self):
        """
        Test that a user with the manage users permission can remove a user with a subset role.
        """
        admin = self.create_admin()
        member = self.add_member()
        self.client.force_authenticate(admin)
        response = self.client.delete(self.get_detail_url(member))
        self.assertEqual(response.status_code, 204, response.data)
        member.refresh_from_db()
        self.assertTrue(member.deleted)

    def test_remove_user_as_user_without_permission(self):
        """
        Test that a user without the manage users permission cannot remove users.
        """
        actor = self.add_member(role=self.viewer_role).user
        member = self.add_member(self.child_organization)
        self.client.force_authenticate(actor)
        response = self.client.delete(
            self.get_detail_url(member, self.child_organization)
        )
        self.assertEqual(response.status_code, 403, response.data)
        member.refresh_from_db()
        self.assertFalse(member.deleted)

    def test_remove_user_with_role_exceeding_own_permissions(self):
        """
        Test that a user cannot remove someone whose role has permissions they do not have.
        """
        higher_role = self.create_role_with_permissions(
            permissions=[
                FacilityOrganizationPermissions.can_view_facility_organization.name,
                FacilityOrganizationPermissions.can_delete_facility_organization.name,
            ]
        )
        member = self.add_member(self.child_organization, role=higher_role)
        admin = self.create_admin()
        self.client.force_authenticate(admin)
        response = self.client.delete(
            self.get_detail_url(member, self.child_organization)
        )
        self.assertEqual(response.status_code, 403, response.data)
        member.refresh_from_db()
        self.assertFalse(member.deleted)

    def test_remove_last_user_from_root_organization(self):
        """
        Test that the last user of a root organization cannot be removed.
        """
        user = self.create_user()
        facility = self.create_facility(user=user)
        root = facility.default_internal_organization
        org_user = FacilityOrganizationUser.objects.get(organization=root, user=user)
        self.client.force_authenticate(self.super_user)
        url = reverse(
            "facility-organization-users-detail",
            kwargs={
                "facility_external_id": facility.external_id,
                "facility_organizations_external_id": root.external_id,
                "external_id": org_user.external_id,
            },
        )
        response = self.client.delete(url)
        self.assertContains(
            response,
            "Cannot delete the last user from the root organization",
            status_code=400,
        )
        org_user.refresh_from_db()
        self.assertFalse(org_user.deleted)

    def test_remove_user_from_root_organization_with_other_users(self):
        """
        Test that a user can be removed from a root organization when other users remain.
        """
        member = self.add_member()
        self.client.force_authenticate(self.super_user)
        response = self.client.delete(self.get_detail_url(member))
        self.assertEqual(response.status_code, 204, response.data)

    def test_remove_last_user_from_non_root_organization(self):
        """
        Test that the last user of a non-root organization can be removed.
        """
        member = self.add_member(self.child_organization)
        self.client.force_authenticate(self.super_user)
        response = self.client.delete(
            self.get_detail_url(member, self.child_organization)
        )
        self.assertEqual(response.status_code, 204, response.data)

    def test_remove_user_without_authentication(self):
        """
        Test that an unauthenticated request cannot remove a user from an organization.
        """
        member = self.add_member(self.child_organization)
        response = self.client.delete(
            self.get_detail_url(member, self.child_organization)
        )
        self.assertEqual(response.status_code, 403, response.data)

    def test_remove_user_with_invalid_id(self):
        """
        Test that removing a non-existent organization user returns 404.
        """
        self.client.force_authenticate(self.super_user)
        member = self.add_member()
        member.external_id = uuid.uuid4()
        response = self.client.delete(self.get_detail_url(member))
        self.assertEqual(response.status_code, 404, response.data)


class FacilityOrganizationAPITests(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.superuser = self.create_super_user()
        self.facility = self.create_facility(user=self.user)
        self.root_facility_organization = self.facility.default_internal_organization
        self.facility_organization = self.create_facility_organization(self.facility)
        self.role = self.create_role_with_permissions(
            permissions=[
                FacilityOrganizationPermissions.can_view_facility_organization.name,
                FacilityOrganizationPermissions.can_create_facility_organization.name,
                FacilityOrganizationPermissions.can_delete_facility_organization.name,
                FacilityOrganizationPermissions.can_manage_facility_organization.name,
            ]
        )

    def get_url(self, facility):
        return reverse(
            "facility-organization-list", kwargs={"facility_external_id": facility}
        )

    def get_detail_url(self, facility, external_id):
        return reverse(
            "facility-organization-detail",
            kwargs={
                "facility_external_id": facility,
                "external_id": external_id,
            },
        )

    def generate_facility_organization_data(self):
        return {
            "name": "Test Facility Organization",
            "description": "Test Description",
            "org_type": "dept",
        }

    # Testcases for creating facility organizations
    def test_create_facility_organization_as_superuser(self):
        """
        Test that a superuser can create a facility organization.
        """
        self.client.force_authenticate(self.superuser)
        url = self.get_url(self.facility.external_id)
        data = self.generate_facility_organization_data()
        response = self.client.post(url, data=data, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["name"], data["name"])

    def test_create_facility_organization_as_user_without_permission(self):
        """
        Test that a regular user cannot create a facility organization.
        """
        self.client.force_authenticate(self.user)
        url = self.get_url(self.facility.external_id)
        data = self.generate_facility_organization_data()
        response = self.client.post(url, data=data, format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.assertIn("detail", response.data)
        self.assertEqual(
            response.data["detail"],
            "User does not have the required permissions to create organizations",
        )

    def test_create_facility_organization_as_user_with_permission(self):
        """
        Test that a regular user with the appropriate permission can create a facility organization.
        """
        self.client.force_authenticate(self.user)
        self.attach_role_facility_organization_user(
            self.root_facility_organization, self.user, self.role
        )
        url = self.get_url(self.facility.external_id)
        data = self.generate_facility_organization_data()
        response = self.client.post(url, data=data, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["name"], data["name"])

    def test_create_create_facility_organization_with_a_parent(self):
        """
        Test that a facility organization can be created with a parent organization.
        """
        self.client.force_authenticate(self.superuser)
        url = self.get_url(self.facility.external_id)
        data = self.generate_facility_organization_data()
        facility_organization = self.create_facility_organization(
            facility=self.facility,
        )
        data["parent"] = facility_organization.external_id
        response = self.client.post(url, data=data, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["name"], data["name"])
        self.assertEqual(response.data["parent"]["id"], str(data["parent"]))

    def test_create_facility_organization_with_parent_as_user_with_permission(self):
        """
        Test that a user with create permission can create an organization under a parent.
        """
        self.attach_role_facility_organization_user(
            self.root_facility_organization, self.user, self.role
        )
        self.client.force_authenticate(self.user)
        data = self.generate_facility_organization_data()
        data["parent"] = self.facility_organization.external_id
        response = self.client.post(
            self.get_url(self.facility.external_id), data=data, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            response.data["parent"]["id"], str(self.facility_organization.external_id)
        )

    def test_create_facility_organization_with_parent_as_user_without_permission(self):
        """
        Test that a user without create permission cannot create an organization under a parent.
        """
        self.client.force_authenticate(self.user)
        data = self.generate_facility_organization_data()
        data["parent"] = self.facility_organization.external_id
        response = self.client.post(
            self.get_url(self.facility.external_id), data=data, format="json"
        )
        self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(
            response.data["detail"],
            "User does not have the required permissions to create organizations",
        )

    def test_create_facility_organization_with_invalid_parent(self):
        """
        Test that creating a facility organization with an invalid parent fails.
        """
        self.client.force_authenticate(self.superuser)
        url = self.get_url(self.facility.external_id)
        data = self.generate_facility_organization_data()
        data["parent"] = uuid.uuid4()
        response = self.client.post(url, data=data, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(
            response.data["errors"][0]["msg"], "Value error, Parent not found"
        )

    def test_create_root_facility_organization(self):
        """
        Test that a root facility organization cannot be created.
        """
        self.client.force_authenticate(self.superuser)
        url = self.get_url(self.facility.external_id)
        data = self.generate_facility_organization_data()
        data["org_type"] = "root"
        response = self.client.post(url, data=data, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(
            response.data["errors"][0]["msg"], "Cannot create root organization"
        )

    def test_create_facility_organization_with_root_org_as_parent(self):
        """
        Test that creating a facility organization with a root organization as parent fails.
        """
        self.client.force_authenticate(self.superuser)
        url = self.get_url(self.facility.external_id)
        data = self.generate_facility_organization_data()
        data["parent"] = self.root_facility_organization.external_id
        response = self.client.post(url, data=data, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "Cannot create organizations under root organization",
        )

    def test_create_facility_organization_with_role_org_as_parent(self):
        """
        Test that creating a facility organization with a role organization as parent fails.
        """
        self.client.force_authenticate(self.superuser)
        url = self.get_url(self.facility.external_id)
        data = self.generate_facility_organization_data()
        role_organization = self.create_facility_organization(
            facility=self.facility, org_type="role"
        )
        data["parent"] = role_organization.external_id
        response = self.client.post(url, data=data, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "Cannot create nested facility organizations under 'role' type facility organization",
        )

    @override_settings(FACILITY_ORGANIZATION_MAX_DEPTH=1)
    def test_create_facility_organization_exceeding_max_depth(self):
        """
        Test that creating a facility organization exceeding the max depth fails.
        """
        self.client.force_authenticate(self.superuser)
        url = self.get_url(self.facility.external_id)
        data = self.generate_facility_organization_data()
        parent = self.create_facility_organization(self.facility)
        child = self.create_facility_organization(self.facility, parent=parent)
        data["parent"] = child.external_id
        response = self.client.post(url, data=data, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            f"Max depth reached ({settings.FACILITY_ORGANIZATION_MAX_DEPTH})",
        )

    @override_settings(MAX_ORGANIZATION_IN_FACILITY=1)
    def test_create_facility_organization_exceeding_max_organizations_in_facility(self):
        """
        Test that creating a facility organization exceeding the max organizations in a facility fails.
        """
        self.client.force_authenticate(self.superuser)
        url = self.get_url(self.facility.external_id)
        data = self.generate_facility_organization_data()
        self.create_facility_organization(self.facility)
        response = self.client.post(url, data=data, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            f"Max location reached for facility ({settings.MAX_ORGANIZATION_IN_FACILITY})",
        )

    def test_create_facility_organization_with_duplicate_name(self):
        """
        Test that creating a facility organization with a duplicate name fails.
        """
        self.client.force_authenticate(self.superuser)
        url = self.get_url(self.facility.external_id)
        data = self.generate_facility_organization_data()
        self.create_facility_organization(self.facility, name=data["name"])
        response = self.client.post(url, data=data, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "Organization already exists with same name",
        )

    # Testcases for updating facility organizations

    def test_update_facility_organization_as_superuser(self):
        """
        Test that updating a facility organization as a superuser succeeds.
        """
        self.client.force_authenticate(self.superuser)
        organization = self.create_facility_organization(self.facility)
        url = self.get_detail_url(self.facility.external_id, organization.external_id)
        data = self.generate_facility_organization_data()
        response = self.client.put(url, data=data, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["name"], data["name"])
        self.assertEqual(response.data["org_type"], data["org_type"])

    def test_update_facility_organization_as_user_without_permission(self):
        """
        Test that updating a facility organization as a non-superuser without permission fails.
        """
        view_only_role = self.create_role_with_permissions(
            permissions=[
                FacilityOrganizationPermissions.can_view_facility_organization.name,
            ]
        )
        self.attach_role_facility_organization_user(
            self.root_facility_organization, self.user, view_only_role
        )
        self.client.force_authenticate(self.user)
        organization = self.create_facility_organization(self.facility)
        url = self.get_detail_url(self.facility.external_id, organization.external_id)
        data = self.generate_facility_organization_data()
        response = self.client.put(url, data=data, format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(
            response.data["detail"],
            "User does not have the required permissions to update organization",
        )

    def test_update_facility_organization_as_user_with_permission(self):
        """
        Test that updating a facility organization as a non-superuser with permission succeeds.
        """
        manage_role = self.create_role_with_permissions(
            permissions=[
                FacilityOrganizationPermissions.can_manage_facility_organization.name,
                FacilityOrganizationPermissions.can_view_facility_organization.name,
            ]
        )
        self.attach_role_facility_organization_user(
            self.root_facility_organization, self.user, manage_role
        )
        self.client.force_authenticate(self.user)
        organization = self.create_facility_organization(self.facility)
        url = self.get_detail_url(self.facility.external_id, organization.external_id)
        data = self.generate_facility_organization_data()
        response = self.client.put(url, data=data, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["name"], data["name"])
        self.assertEqual(response.data["org_type"], data["org_type"])

    def test_update_root_facility_organization(self):
        """
        Test that updating a root facility organization fails.
        """
        self.client.force_authenticate(self.superuser)
        url = self.get_detail_url(
            self.facility.external_id, self.root_facility_organization.external_id
        )
        data = self.generate_facility_organization_data()
        response = self.client.put(url, data=data, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(
            response.data["errors"][0]["msg"], "Cannot update root organization"
        )

    def test_update_facility_organization_with_duplicate_name(self):
        """
        Test that updating a facility organization with a duplicate name fails.
        """
        self.client.force_authenticate(self.superuser)
        organization = self.create_facility_organization(self.facility)
        data = self.generate_facility_organization_data()
        self.create_facility_organization(self.facility, name=data["name"])
        url = self.get_detail_url(self.facility.external_id, organization.external_id)
        response = self.client.put(url, data=data, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "Organization already exists with same name",
        )

    # Testcases for deleting facility organizations

    def test_delete_facility_organization_as_superuser(self):
        """
        Test that deleting a facility organization as a superuser.
        """
        self.client.force_authenticate(self.superuser)
        organization = self.create_facility_organization(self.facility)
        url = self.get_detail_url(self.facility.external_id, organization.external_id)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)

    def test_delete_facility_organization_updates_parent_has_children(self):
        """
        Test that deleting a child organization updates has_children on the parent.
        """
        self.client.force_authenticate(self.superuser)
        parent = self.create_facility_organization(self.facility, org_type="dept")
        child = self.create_facility_organization(
            self.facility, org_type="team", parent=parent
        )
        sibling = self.create_facility_organization(
            self.facility, org_type="team", parent=parent
        )
        parent.refresh_from_db()
        self.assertTrue(parent.has_children)

        response = self.client.delete(
            self.get_detail_url(self.facility.external_id, child.external_id)
        )
        self.assertEqual(response.status_code, 204)
        parent.refresh_from_db()
        self.assertTrue(parent.has_children)
        self.assertEqual(parent.updated_by, self.superuser)

        response = self.client.delete(
            self.get_detail_url(self.facility.external_id, sibling.external_id)
        )
        self.assertEqual(response.status_code, 204)
        parent.refresh_from_db()
        self.assertFalse(parent.has_children)

    def test_delete_root_facility_organization(self):
        """
        Test that deleting a root facility organization fails.
        """
        self.client.force_authenticate(self.superuser)
        url = self.get_detail_url(
            self.facility.external_id, self.root_facility_organization.external_id
        )
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(
            response.data["errors"][0]["msg"], "Cannot delete root organization"
        )

    def test_delete_facility_organization_with_children(self):
        """
        Test that deleting a facility organization with children fails.
        """
        self.client.force_authenticate(self.superuser)
        parent_organization = self.create_facility_organization(self.facility)
        self.create_facility_organization(self.facility, parent=parent_organization)
        url = self.get_detail_url(
            self.facility.external_id, parent_organization.external_id
        )
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "Cannot delete organization with children",
        )

    def test_delete_facility_organization_with_users(self):
        """
        Test that deleting a facility organization with users fails.
        """
        self.client.force_authenticate(self.superuser)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        url = self.get_detail_url(
            self.facility.external_id, self.facility_organization.external_id
        )
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(
            response.data["errors"][0]["msg"], "Cannot delete organization with users"
        )

    def test_delete_facility_organization_with_encounters(self):
        """
        Test that deleting a facility organization with encounters fails.
        """
        self.client.force_authenticate(self.superuser)
        patient = self.create_patient()
        self.create_encounter(
            organization=self.facility_organization,
            facility=self.facility,
            patient=patient,
        )
        url = self.get_detail_url(
            self.facility.external_id, self.facility_organization.external_id
        )
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "Cannot delete organization with encounters",
        )

    def create_location(self):
        return baker.make(FacilityLocation, facility=self.facility)

    def attach_location_to_organization(self, location, organization):
        return baker.make(
            FacilityLocationOrganization, location=location, organization=organization
        )

    def test_delete_facility_organization_with_location(self):
        """
        Test that deleting a facility organization with locations fails.
        """
        self.client.force_authenticate(self.superuser)
        location = self.create_location()
        self.attach_location_to_organization(location, self.facility_organization)
        url = self.get_detail_url(
            self.facility.external_id, self.facility_organization.external_id
        )
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "Cannot delete organization with locations",
        )

    def test_delete_facility_organization_with_device(self):
        """
        Test that deleting a facility organization with devices fails.
        """
        self.client.force_authenticate(self.superuser)
        baker.make(
            Device,
            facility=self.facility,
            managing_organization=self.facility_organization,
        )
        url = self.get_detail_url(
            self.facility.external_id, self.facility_organization.external_id
        )
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(
            response.data["errors"][0]["msg"], "Cannot delete organization with devices"
        )

    def test_delete_facility_organization_as_user_with_permission(self):
        """
        Test that a user with the appropriate permission can delete a facility organization.
        """
        self.client.force_authenticate(self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        url = self.get_detail_url(
            self.facility.external_id, self.facility_organization.external_id
        )
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)

    def test_delete_facility_organization_as_user_without_permission(self):
        """
        Test that a user without the appropriate permission cannot delete a facility organization.
        """
        self.client.force_authenticate(self.user)
        manage_role = self.create_role_with_permissions(
            permissions=[
                FacilityOrganizationPermissions.can_manage_facility_organization.name,
                FacilityOrganizationPermissions.can_view_facility_organization.name,
            ]
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, manage_role
        )
        url = self.get_detail_url(
            self.facility.external_id, self.facility_organization.external_id
        )
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(
            response.data["detail"],
            "User does not have the required permissions to delete this organization",
        )

    # Testcases for listing facility organizations

    def get_mine_url(self, facility):
        return reverse(
            "facility-organization-mine", kwargs={"facility_external_id": facility}
        )

    def list_ids(self, response):
        return {result["id"] for result in response.data["results"]}

    def test_list_facility_organizations_as_superuser(self):
        """
        Test that a superuser can list all organizations of a facility, including root.
        """
        self.client.force_authenticate(self.superuser)
        response = self.client.get(self.get_url(self.facility.external_id))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(
            self.list_ids(response),
            {
                str(self.root_facility_organization.external_id),
                str(self.facility_organization.external_id),
            },
        )

    def test_list_facility_organizations_without_authentication(self):
        """
        Test that an unauthenticated user cannot list facility organizations.
        """
        response = self.client.get(self.get_url(self.facility.external_id))
        self.assertEqual(response.status_code, 403, response.data)

    def test_list_facility_organizations_as_user_without_permission(self):
        """
        Test that a user with no permission gets an empty list.
        """
        self.client.force_authenticate(self.user)
        response = self.client.get(self.get_url(self.facility.external_id))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 0)

    def test_list_facility_organizations_as_user_with_permission_on_root(self):
        """
        Test that a user with view permission on the root organization can see all organizations.
        """
        self.attach_role_facility_organization_user(
            self.root_facility_organization, self.user, self.role
        )
        self.client.force_authenticate(self.user)
        response = self.client.get(self.get_url(self.facility.external_id))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            self.list_ids(response),
            {
                str(self.root_facility_organization.external_id),
                str(self.facility_organization.external_id),
            },
        )

    def test_list_facility_organizations_as_user_with_permission_on_non_root(self):
        """
        Test that a user with view permission only on a non-root organization cannot see the root organization.
        """
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(self.user)
        response = self.client.get(self.get_url(self.facility.external_id))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            self.list_ids(response), {str(self.facility_organization.external_id)}
        )

    def test_list_facility_organizations_with_invalid_facility(self):
        """
        Test that listing organizations of a non-existent facility returns 404.
        """
        self.client.force_authenticate(self.superuser)
        response = self.client.get(self.get_url(uuid.uuid4()))
        self.assertEqual(response.status_code, 404, response.data)

    def test_list_facility_organizations_excludes_other_facilities(self):
        """
        Test that organizations of other facilities are not listed.
        """
        other_facility = self.create_facility(user=self.user)
        other_organization = self.create_facility_organization(other_facility)
        self.client.force_authenticate(self.superuser)
        response = self.client.get(self.get_url(self.facility.external_id))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertNotIn(str(other_organization.external_id), self.list_ids(response))
        self.assertEqual(response.data["count"], 2)

    def test_list_facility_organizations_excludes_deleted(self):
        """
        Test that deleted organizations are not listed.
        """
        deleted_organization = self.create_facility_organization(
            self.facility, deleted=True
        )
        self.client.force_authenticate(self.superuser)
        response = self.client.get(self.get_url(self.facility.external_id))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertNotIn(str(deleted_organization.external_id), self.list_ids(response))

    def test_list_facility_organizations_filter_by_name(self):
        """
        Test that organizations can be filtered by a case-insensitive partial name.
        """
        organization = self.create_facility_organization(
            self.facility, name="Cardiology Department"
        )
        self.client.force_authenticate(self.superuser)
        response = self.client.get(
            self.get_url(self.facility.external_id), {"name": "cardio"}
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.list_ids(response), {str(organization.external_id)})

        response = self.client.get(
            self.get_url(self.facility.external_id), {"name": "no-such-name"}
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 0)

    def test_list_facility_organizations_filter_by_org_type(self):
        """
        Test that organizations can be filtered by org_type.
        """
        team = self.create_facility_organization(
            self.facility, name="Team A", org_type="team"
        )
        self.create_facility_organization(self.facility, name="Dept A", org_type="dept")
        self.client.force_authenticate(self.superuser)
        response = self.client.get(
            self.get_url(self.facility.external_id), {"org_type": "TEAM"}
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.list_ids(response), {str(team.external_id)})

        response = self.client.get(
            self.get_url(self.facility.external_id), {"org_type": "root"}
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            self.list_ids(response), {str(self.root_facility_organization.external_id)}
        )

    def test_list_facility_organizations_filter_by_parent(self):
        """
        Test that organizations can be filtered by parent.
        """
        parent = self.create_facility_organization(
            self.facility, name="Parent", org_type="dept"
        )
        child = self.create_facility_organization(
            self.facility, name="Child", org_type="team", parent=parent
        )
        self.client.force_authenticate(self.superuser)
        response = self.client.get(
            self.get_url(self.facility.external_id), {"parent": parent.external_id}
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.list_ids(response), {str(child.external_id)})
        self.assertEqual(
            response.data["results"][0]["parent"]["id"], str(parent.external_id)
        )

    def test_list_facility_organizations_filter_by_empty_parent(self):
        """
        Test that an empty parent filter returns only top level organizations.
        """
        parent = self.create_facility_organization(
            self.facility, name="Parent", org_type="dept"
        )
        child = self.create_facility_organization(
            self.facility, name="Child", org_type="team", parent=parent
        )
        self.client.force_authenticate(self.superuser)
        response = self.client.get(
            self.get_url(self.facility.external_id), {"parent": ""}
        )
        self.assertEqual(response.status_code, 200, response.data)
        ids = self.list_ids(response)
        self.assertIn(str(parent.external_id), ids)
        self.assertIn(str(self.root_facility_organization.external_id), ids)
        self.assertNotIn(str(child.external_id), ids)

    def test_list_facility_organizations_filter_by_containing_user(self):
        """
        Test that organizations can be filtered by a user attached to them.
        """
        member = self.create_user()
        self.attach_role_facility_organization_user(
            self.facility_organization, member, self.role
        )
        self.create_facility_organization(self.facility, name="Unrelated")
        self.client.force_authenticate(self.superuser)
        response = self.client.get(
            self.get_url(self.facility.external_id),
            {"containing_user": member.external_id},
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            self.list_ids(response), {str(self.facility_organization.external_id)}
        )

    def test_list_facility_organizations_filter_by_invalid_containing_user(self):
        """
        Test that filtering by a non-existent user returns 404.
        """
        self.client.force_authenticate(self.superuser)
        response = self.client.get(
            self.get_url(self.facility.external_id), {"containing_user": uuid.uuid4()}
        )
        self.assertEqual(response.status_code, 404, response.data)

    def test_list_facility_organizations_pagination(self):
        """
        Test that the list is paginated using limit and offset.
        """
        for i in range(3):
            self.create_facility_organization(self.facility, name=f"Paginated {i}")
        self.client.force_authenticate(self.superuser)
        response = self.client.get(
            self.get_url(self.facility.external_id), {"limit": 2, "offset": 0}
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 5)
        self.assertEqual(len(response.data["results"]), 2)

    def test_list_mine_facility_organizations(self):
        """
        Test that the mine endpoint returns only organizations directly attached to the user in the facility.
        """
        member = self.create_user()
        self.attach_role_facility_organization_user(
            self.facility_organization, member, self.role
        )
        other_facility = self.create_facility(user=self.user)
        other_organization = self.create_facility_organization(other_facility)
        self.attach_role_facility_organization_user(
            other_organization, member, self.role
        )
        self.client.force_authenticate(member)
        response = self.client.get(self.get_mine_url(self.facility.external_id))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["id"],
            str(self.facility_organization.external_id),
        )

    def test_list_mine_facility_organizations_without_memberships(self):
        """
        Test that the mine endpoint returns an empty list for a user without memberships.
        """
        self.client.force_authenticate(self.create_user())
        response = self.client.get(self.get_mine_url(self.facility.external_id))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])

    # Testcases for retrieving facility organizations

    def test_retrieve_facility_organization_as_superuser(self):
        """
        Test that a superuser can retrieve a facility organization.
        """
        self.client.force_authenticate(self.superuser)
        url = self.get_detail_url(
            self.facility.external_id, self.facility_organization.external_id
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            response.data["id"], str(self.facility_organization.external_id)
        )
        self.assertEqual(response.data["name"], self.facility_organization.name)
        self.assertEqual(response.data["org_type"], self.facility_organization.org_type)
        self.assertIn("permissions", response.data)

    def test_retrieve_root_facility_organization_as_superuser(self):
        """
        Test that a superuser can retrieve the root organization.
        """
        self.client.force_authenticate(self.superuser)
        url = self.get_detail_url(
            self.facility.external_id, self.root_facility_organization.external_id
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["org_type"], "root")

    def test_retrieve_facility_organization_without_authentication(self):
        """
        Test that an unauthenticated user cannot retrieve a facility organization.
        """
        url = self.get_detail_url(
            self.facility.external_id, self.facility_organization.external_id
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403, response.data)

    def test_retrieve_facility_organization_as_user_without_permission(self):
        """
        Test that a user without view permission cannot retrieve a facility organization.
        """
        self.client.force_authenticate(self.user)
        url = self.get_detail_url(
            self.facility.external_id, self.facility_organization.external_id
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404, response.data)

    def test_retrieve_facility_organization_as_user_with_permission(self):
        """
        Test that a user with view permission can retrieve an organization and sees their permissions on it.
        """
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(self.user)
        url = self.get_detail_url(
            self.facility.external_id, self.facility_organization.external_id
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            response.data["id"], str(self.facility_organization.external_id)
        )
        self.assertIn(
            FacilityOrganizationPermissions.can_view_facility_organization.name,
            response.data["permissions"],
        )

    def test_retrieve_root_facility_organization_with_permission_only_on_non_root(self):
        """
        Test that a user with permission only on a non-root organization cannot retrieve the root organization.
        """
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(self.user)
        url = self.get_detail_url(
            self.facility.external_id, self.root_facility_organization.external_id
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404, response.data)

    def test_retrieve_facility_organization_with_parent(self):
        """
        Test that the parent details are returned for a nested organization.
        """
        parent = self.create_facility_organization(
            self.facility, name="Parent", org_type="dept"
        )
        child = self.create_facility_organization(
            self.facility, name="Child", org_type="team", parent=parent
        )
        self.client.force_authenticate(self.superuser)
        url = self.get_detail_url(self.facility.external_id, child.external_id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["parent"]["id"], str(parent.external_id))
        self.assertEqual(response.data["parent"]["name"], parent.name)

    def test_retrieve_facility_organization_with_invalid_id(self):
        """
        Test that retrieving a non-existent organization returns 404.
        """
        self.client.force_authenticate(self.superuser)
        url = self.get_detail_url(self.facility.external_id, uuid.uuid4())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404, response.data)

    def test_retrieve_facility_organization_with_invalid_facility(self):
        """
        Test that retrieving an organization under a non-existent facility returns 404.
        """
        self.client.force_authenticate(self.superuser)
        url = self.get_detail_url(uuid.uuid4(), self.facility_organization.external_id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404, response.data)

    def test_retrieve_facility_organization_from_another_facility(self):
        """
        Test that an organization cannot be retrieved through a different facility.
        """
        other_facility = self.create_facility(user=self.user)
        self.client.force_authenticate(self.superuser)
        url = self.get_detail_url(
            other_facility.external_id, self.facility_organization.external_id
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404, response.data)

    def test_retrieve_deleted_facility_organization(self):
        """
        Test that a deleted organization cannot be retrieved.
        """
        deleted_organization = self.create_facility_organization(
            self.facility, deleted=True
        )
        self.client.force_authenticate(self.superuser)
        url = self.get_detail_url(
            self.facility.external_id, deleted_organization.external_id
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404, response.data)
