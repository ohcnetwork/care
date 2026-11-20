from django.urls import reverse

from care.emr.models.valueset import ValueSet
from care.emr.models.workspace import Workspace
from care.security.authorization.valueset import ValueSetAccess
from care.security.authorization.workspace import WorkspaceAccess
from care.security.permissions.valueset import ValueSetPermissions
from care.security.permissions.workspace import WorkspacePermissions
from care.utils.tests.base import CareAPITestBase


class WorkspaceAndValueSetReadAuthorizationTests(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(self.user)
        self.department = self.create_facility_organization(
            self.facility, parent=self.facility.default_internal_organization
        )
        self.sibling = self.create_facility_organization(
            self.facility, parent=self.facility.default_internal_organization
        )
        self.other_facility = self.create_facility(self.user)
        self.other_department = self.create_facility_organization(self.other_facility)
        role = self.create_role_with_permissions(
            [
                ValueSetPermissions.can_read_valueset.name,
                WorkspacePermissions.can_read_workspace.name,
            ]
        )
        self.attach_role_facility_organization_user(self.department, self.user, role)

    def test_department_read_permissions_do_not_grant_write_or_sibling_access(self):
        handlers = [
            ValueSetAccess().can_access_facility_organization_valueset,
            WorkspaceAccess().can_access_facility_organization_workspace,
        ]
        for handler in handlers:
            with self.subTest(handler=handler.__name__):
                self.assertTrue(handler(self.user, self.department, read_only=True))
                self.assertFalse(handler(self.user, self.department, read_only=False))
                self.assertFalse(handler(self.user, self.sibling, read_only=True))
                self.assertFalse(
                    handler(self.user, self.other_department, read_only=True)
                )

    def test_facility_read_requires_membership_in_the_assigned_organizations(self):
        scoped_resources = [
            (ValueSetAccess().can_access_facility_valueset, ValueSet()),
            (WorkspaceAccess().can_access_facility_workspace, Workspace()),
        ]
        for handler, resource in scoped_resources:
            with self.subTest(handler=handler.__name__):
                resource.internal_organization_cache = [self.department.pk]
                self.assertTrue(
                    handler(self.user, self.facility, resource, read_only=True)
                )
                self.assertFalse(
                    handler(self.user, self.other_facility, resource, read_only=True)
                )
                resource.internal_organization_cache = [self.sibling.pk]
                self.assertFalse(
                    handler(self.user, self.facility, resource, read_only=True)
                )
                resource.internal_organization_cache = []
                self.assertFalse(
                    handler(self.user, self.facility, resource, read_only=True)
                )

    def test_personal_scope_read_permission_is_restricted_to_the_facility(self):
        handlers = [
            ValueSetAccess().can_access_user_valueset_in_faciltiy,
            WorkspaceAccess().can_access_user_workspace_in_facility,
        ]
        for handler in handlers:
            with self.subTest(handler=handler.__name__):
                self.assertTrue(handler(self.user, self.facility, read_only=True))
                self.assertFalse(handler(self.user, self.facility, read_only=False))
                self.assertFalse(
                    handler(self.user, self.other_facility, read_only=True)
                )

    def test_department_writer_can_create_a_valueset_scoped_to_their_department(self):
        role = self.create_role_with_permissions(
            [ValueSetPermissions.can_write_valueset.name]
        )
        self.attach_role_facility_organization_user(self.department, self.user, role)
        self.client.force_authenticate(self.user)

        response = self.client.post(
            reverse("value-set-list"),
            {
                "slug": "department-codes",
                "name": "Department codes",
                "description": "Clinical codes for the department",
                "status": "active",
                "compose": {"include": [], "exclude": []},
                "auth_context": "facility_organization",
                "facility_organization": str(self.department.external_id),
                "disable_composition": False,
                "inherited": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        valueset = ValueSet.objects.get(external_id=response.data["id"])
        self.assertEqual(valueset.facility, self.facility)
        self.assertEqual(valueset.facility_organization, self.department)
        self.assertEqual(valueset.created_by, self.user)
        self.assertCountEqual(
            valueset.internal_organization_cache,
            [self.facility.default_internal_organization.pk, self.department.pk],
        )
