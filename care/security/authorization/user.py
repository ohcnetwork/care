from care.emr.models.organization import FacilityOrganizationUser, OrganizationUser
from care.security.authorization.base import (
    AuthorizationController,
    AuthorizationHandler,
)
from care.security.permissions.user import UserPermissions


class UserAccess(AuthorizationHandler):
    def can_create_user(self, user):
        """
        Check if the user has permission to create a user
        """
        if user.is_superuser:
            return True
        roles = self.get_role_from_permissions([UserPermissions.can_create_user.name])
        return (
            OrganizationUser.objects.filter(user=user, role_id__in=roles).exists()
            or FacilityOrganizationUser.objects.filter(
                user=user, role_id__in=roles
            ).exists()
        )


AuthorizationController.register_internal_controller(UserAccess)
