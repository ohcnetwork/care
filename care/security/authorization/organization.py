from django.db.models import Q

from care.emr.models.organization import OrganizationUser
from care.security.authorization.base import (
    AuthorizationController,
    AuthorizationHandler,
)
from care.security.models import RoleModel
from care.security.permissions.organization import OrganizationPermissions


class OrganizationAccess(AuthorizationHandler):
    def can_create_organization_obj(self, user, organization):
        """
        Check if the user has permission to create organizations under the given organization
        """
        return self.check_permission_in_organization(
            [OrganizationPermissions.can_create_organization.name],
            user,
            [*organization.parent_cache, organization.id],
        )

    def can_manage_organization_obj(self, user, organization):
        """
        Check if the user has permission to manage given organization.
        """
        return self.check_permission_in_organization(
            [OrganizationPermissions.can_manage_organization.name],
            user,
            [*organization.parent_cache, organization.id],
        )

    def check_role_subset(self, user, organization_parents, requested_role):
        """
        Check if the requested role is a subset of user's roles in an organization
        """
        # Get users roles on organization, ideally only one role should be present at some level
        user_roles = RoleModel.objects.filter(
            id__in=OrganizationUser.objects.filter(
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

    def can_manage_organization_users_obj(self, user, organization, requested_role):
        """
        Check if the user has permission to create organizations under the given organization
        """
        if user.is_superuser:
            return True
        organization_parents = [*organization.parent_cache, organization.id]

        if not self.check_role_subset(user, organization_parents, requested_role):
            return False

        return self.check_permission_in_organization(
            [OrganizationPermissions.can_manage_organization_users.name],
            user,
            organization_parents,
        )

    def can_list_organization_users_obj(self, user, organization):
        """
        Check if the user has permission to create organizations under the given organization
        """
        return self.check_permission_in_organization(
            [OrganizationPermissions.can_list_organization_users.name],
            user,
            [*organization.parent_cache, organization.id],
        )

    def can_delete_organization(self, user, organization):
        """
        Check if the user has permission to delete the given organization
        """
        return self.check_permission_in_organization(
            [OrganizationPermissions.can_delete_organization.name],
            user,
            [*organization.parent_cache, organization.id],
        )

    def get_accessible_organizations(self, qs, user):
        from care.emr.resources.organization.spec import OrganizationTypeChoices

        if user.is_superuser:
            return qs
        roles = self.get_role_from_permissions(
            [OrganizationPermissions.can_view_organization.name]
        )
        organization_ids = list(
            OrganizationUser.objects.filter(user=user, role_id__in=roles).values_list(
                "organization_id", flat=True
            )
        )
        return qs.filter(
            Q(parent_cache__overlap=organization_ids)
            | Q(
                org_type__in=[
                    OrganizationTypeChoices.govt.value,
                    OrganizationTypeChoices.product_supplier.value,
                ]
            )
            | Q(id__in=organization_ids)
        )

    def get_permission_on_organization(self, organization, user):
        organization_parents = [*organization.parent_cache, organization.id]
        user_roles = RoleModel.objects.filter(
            id__in=OrganizationUser.objects.filter(
                organization_id__in=organization_parents, user=user
            ).values("role_id")
        )
        merged_permissions = set()
        for role in user_roles:
            merged_permissions = merged_permissions.union(
                set(role.get_permission_sk_for_role())
            )
        return merged_permissions


AuthorizationController.register_internal_controller(OrganizationAccess)
