from django.urls import reverse

from care.security.permissions.facility_organization import (
    FacilityOrganizationPermissions,
)
from care.utils.tests.base import CareAPITestBase


class FacilityOrganizationDeleteValidationTests(CareAPITestBase):
    def setUp(self):
        self.super_user = self.create_super_user()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.facility_root_org = self.facility.default_internal_organization
        self.manage_role = self.create_role_with_permissions(
            permissions=[
                FacilityOrganizationPermissions.can_view_facility_organization.name,
                FacilityOrganizationPermissions.can_delete_facility_organization.name,
            ]
        )

    def _get_url(self, org_id):
        return reverse(
            "facility-organization-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": org_id,
            },
        )

    def test_delete_facility_organization(self):
        facility_org = self.create_facility_organization(
            facility=self.facility, parent=self.facility_root_org
        )

        org_user_role = self.attach_role_facility_organization_user(
            facility_org, self.user, self.manage_role
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.delete(self._get_url(facility_org.external_id))

        self.assertEqual(response.status_code, 204, f"Response: {response.data}")

        facility_org.refresh_from_db()
        self.assertEqual(
            facility_org.deleted,
            True,
            "Facility organization was not marked as deleted",
        )

        with self.assertRaises(
            org_user_role.DoesNotExist, msg="Organization user role was not deleted"
        ):
            org_user_role.refresh_from_db()

    def test_delete_root_facility_organization(self):
        self.attach_role_facility_organization_user(
            self.facility_root_org, self.user, self.manage_role
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.delete(self._get_url(self.facility_root_org.external_id))

        self.assertEqual(response.status_code, 400, f"Response: {response.data}")
        self.assertContains(
            response,
            "Cannot delete root organization",
            status_code=400,
        )

    def test_delete_facility_organization_without_permission(self):
        facility_org = self.create_facility_organization(
            facility=self.facility, parent=self.facility_root_org
        )

        limited_role = self.create_role_with_permissions(
            permissions=[
                FacilityOrganizationPermissions.can_view_facility_organization.name,
            ]
        )
        self.attach_role_facility_organization_user(
            facility_org, self.user, limited_role
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.delete(self._get_url(facility_org.external_id))

        self.assertEqual(response.status_code, 403, f"Response: {response.data}")

        self.assertContains(
            response,
            "User does not have the required permissions to delete this organization",
            status_code=403,
        )

        facility_org.refresh_from_db()
        self.assertEqual(
            facility_org.deleted,
            False,
            "Facility organization was marked as deleted without permission",
        )

    def test_delete_facility_organization_with_members(self):
        facility_org = self.create_facility_organization(
            facility=self.facility, parent=self.facility_root_org
        )

        member_role = self.create_role_with_permissions(permissions=[])

        self.attach_role_facility_organization_user(
            facility_org, self.create_user(), member_role
        )

        self.attach_role_facility_organization_user(
            facility_org, self.user, self.manage_role
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.delete(self._get_url(facility_org.external_id))

        self.assertEqual(response.status_code, 400, f"Response: {response.data}")

        self.assertContains(
            response,
            "Cannot delete organization with users",
            status_code=400,
        )

    def test_delete_facility_organization_with_children(self):
        facility_org = self.create_facility_organization(
            facility=self.facility, parent=self.facility_root_org
        )

        self.create_facility_organization(facility=self.facility, parent=facility_org)

        self.attach_role_facility_organization_user(
            facility_org, self.user, self.manage_role
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.delete(self._get_url(facility_org.external_id))

        self.assertEqual(response.status_code, 400, f"Response: {response.data}")

        self.assertContains(
            response,
            "Cannot delete organization with children",
            status_code=400,
        )
