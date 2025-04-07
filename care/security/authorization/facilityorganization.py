from care.emr.models import FacilityOrganization
from care.emr.models.organization import FacilityOrganizationUser
from care.security.authorization.base import (
    AuthorizationController,
    AuthorizationHandler,
)
from care.security.models import RoleModel
from care.security.permissions.facility_organization import (
    FacilityOrganizationPermissions,
)


class FacilityOrganizationAccess(AuthorizationHandler):
    def check_role_subset(self, user, organization_parents, requested_role):
        """
        Check if the requested role is a subset of user's roles in an organization
        """
        # Get users roles on organization, ideally only one role should be present at some level
        user_roles = RoleModel.objects.filter(
            id__in=FacilityOrganizationUser.objects.filter(
                organization_id__in=organization_parents, user=user
            ).values("role_id")
        )
        merged_permissions = set()
        # Convert role into a list of permissions for the user
        for role in user_roles:
            merged_permissions = merged_permissions.union(
                set(role.get_permission_sk_for_role())
            )
        # Get the requested role's permissions
        requested_role = set(requested_role.get_permission_sk_for_role())
        # Confirm if requested role's permission are the subset of the users roles
        return requested_role.issubset(merged_permissions)

    def can_create_facility_organization_obj(self, user, organization, facility):
        """
        Check if the user has permission to create organizations under the given organization
        """

        if organization:
            root_organization = FacilityOrganization.objects.get(
                facility=organization.facility, org_type="root"
            )
            return self.check_permission_in_facility_organization(
                [FacilityOrganizationPermissions.can_create_facility_organization.name],
                user,
                [*organization.parent_cache, organization.id, root_organization.id],
            )
        return self.check_permission_in_facility_organization(
            [FacilityOrganizationPermissions.can_create_facility_organization.name],
            user,
            facility=facility,
        )

    def can_manage_facility_organization_obj(self, user, organization):
        """
        Check if the user has permission to manage given organization.
        """
        root_organization = FacilityOrganization.objects.get(
            facility=organization.facility, org_type="root"
        )
        return self.check_permission_in_facility_organization(
            [FacilityOrganizationPermissions.can_manage_facility_organization.name],
            user,
            [*organization.parent_cache, organization.id, root_organization.id],
        )

    def can_delete_facility_organization(self, user, organization):
        """
        Check if the user has permission to delete the given organization
        """
        root_organization = FacilityOrganization.objects.get(
            facility=organization.facility, org_type="root"
        )
        return self.check_permission_in_facility_organization(
            [FacilityOrganizationPermissions.can_delete_facility_organization.name],
            user,
            [*organization.parent_cache, organization.id, root_organization.id],
        )

    def get_accessible_facility_organizations(self, qs, user, facility):
        if user.is_superuser:
            return qs
        permission = self.check_permission_in_facility_organization(
            [FacilityOrganizationPermissions.can_view_facility_organization.name],
            user,
            facility=facility,
        )
        root_facility_organization = FacilityOrganization.objects.get(
            facility=facility, org_type="root"
        )
        root_permission = self.check_permission_in_facility_organization(
            [FacilityOrganizationPermissions.can_view_facility_organization.name],
            user,
            [*root_facility_organization.parent_cache, root_facility_organization.id],
        )
        if root_permission:
            return qs
        if permission:
            return qs.exclude(org_type="root")
        return qs.none()

    def can_list_facility_organization_users_obj(self, user, organization):
        """
        Check if the user has permission to create organizations under the given organization
        """
        return self.check_permission_in_facility_organization(
            [FacilityOrganizationPermissions.can_list_facility_organization_users.name],
            user,
            facility=organization.facility,
        )

    def can_manage_facility_organization_users_obj(
        self, user, organization, requested_role
    ):
        """
        Check if the user has permission manage users in the given organization
        """
        if user.is_superuser:
            return True

        root_organization = FacilityOrganization.objects.get(
            facility=organization.facility, org_type="root"
        )
        organization_parents = [
            *organization.parent_cache,
            organization.id,
            root_organization.id,
        ]

        if not self.check_role_subset(user, organization_parents, requested_role):
            return False

        return self.check_permission_in_facility_organization(
            [
                FacilityOrganizationPermissions.can_manage_facility_organization_users.name
            ],
            user,
            organization_parents,
        )

    def get_permission_on_facility_organization(self, organization, user):
        organization_parents = [*organization.parent_cache, organization.id]
        user_roles = RoleModel.objects.filter(
            id__in=FacilityOrganizationUser.objects.filter(
                organization_id__in=organization_parents, user=user
            ).values("role_id")
        )
        merged_permissions = set()
        for role in user_roles:
            merged_permissions = merged_permissions.union(
                set(role.get_permission_sk_for_role())
            )
        return merged_permissions


AuthorizationController.register_internal_controller(FacilityOrganizationAccess)
