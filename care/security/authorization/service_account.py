from care.emr.models.organization import FacilityOrganizationUser, OrganizationUser
from care.security.authorization.base import (
    AuthorizationController,
    AuthorizationHandler,
)
from care.security.permissions.service_account import ServiceAccountPermissions


class ServiceAccountAccess(AuthorizationHandler):
    def can_create_service_account(self, user):
        """
        Check if the user has permission to create a service account
        """
        if user.is_superuser:
            return True
        roles = self.get_role_from_permissions(
            [ServiceAccountPermissions.can_create_service_account.name]
        )
        return (
            OrganizationUser.objects.filter(user=user, role_id__in=roles).exists()
            or FacilityOrganizationUser.objects.filter(
                user=user, role_id__in=roles
            ).exists()
        )


AuthorizationController.register_internal_controller(ServiceAccountAccess)
