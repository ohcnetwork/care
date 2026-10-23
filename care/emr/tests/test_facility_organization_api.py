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
