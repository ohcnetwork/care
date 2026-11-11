from django.db.models import Q

from care.emr.models.organization import FacilityOrganizationUser, OrganizationUser
from care.security.authorization.base import (
    AuthorizationController,
    AuthorizationHandler,
)
from care.security.permissions.workspace import WorkspacePermissions


class WorkspaceAccess(AuthorizationHandler):
    def can_access_facility_workspace(self, user, facility, workspace, read_only):
        """
        Permission to access a workspace for a specific facility
        """
        if read_only:
            permission = [WorkspacePermissions.can_read_workspace.name]
            return self.check_permission_in_facility_organization(
                permission,
                user,
                facility=facility,
                orgs=workspace.internal_organization_cache,
            )
        permission = [WorkspacePermissions.can_write_workspace.name]
        return self.check_permission_in_facility_organization(
            permission, user, facility=facility, root=True
        )

    def can_access_facility_organization_workspace(
        self, user, facility_organization, read_only
    ):
        """
        Permission to access a workspace for a specific facility organization
        """
        if read_only:
            permission = [WorkspacePermissions.can_read_workspace.name]
        else:
            permission = [WorkspacePermissions.can_write_workspace.name]
        return self.check_permission_in_facility_organization(
            permission,
            user,
            facility=facility_organization.facility,
            orgs=[*facility_organization.parent_cache, facility_organization.id],
        )

    def can_access_user_workspace_in_facility(self, user, facility, read_only):
        """
        Permission to write a workspace for a specific facility as a user
        """
        if read_only:
            permission = [WorkspacePermissions.can_read_workspace.name]
        else:
            permission = [WorkspacePermissions.can_write_workspace.name]
        return self.check_permission_in_facility_organization(
            permission,
            user,
            facility=facility,
        )

    def get_filtered_workspaces(self, qs, user):
        if user.is_superuser:
            return qs
        roles = self.get_role_from_permissions(
            [WorkspacePermissions.can_read_workspace.name]
        )
        facility_organization_ids = list(
            FacilityOrganizationUser.objects.filter(
                user=user, role_id__in=roles
            ).values_list("organization_id", flat=True)
        )
        organization_ids = list(
            OrganizationUser.objects.filter(user=user, role_id__in=roles).values_list(
                "organization_id", flat=True
            )
        )
        write_roles = self.get_role_from_permissions(
            [WorkspacePermissions.can_write_workspace.name]
        )
        writable_facility_ids = FacilityOrganizationUser.objects.filter(
            user=user,
            role_id__in=write_roles,
            organization__org_type="root",
        ).values_list("organization__facility_id", flat=True)
        return qs.filter(
            Q(auth_context="instance", organization_cache__overlap=organization_ids)
            | Q(internal_organization_cache__overlap=facility_organization_ids)
            | Q(auth_context="user", created_by=user)
            | Q(auth_context="facility", facility_id__in=writable_facility_ids)
        )


AuthorizationController.register_internal_controller(WorkspaceAccess)
