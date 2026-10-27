from care.security.authorization.base import (
    AuthorizationController,
    AuthorizationHandler,
)
from care.security.permissions.immunization import ImmunizationPermissions


class ImmunizationAccess(AuthorizationHandler):
    def can_list_facility_immunization_policy(self, user, facility):
        """
        Check if the user has permission to view immunization policies in the facility
        """
        return self.check_permission_in_facility_organization(
            [ImmunizationPermissions.can_read_immunization_policy.name],
            user,
            facility=facility,
        )

    def can_write_facility_immunization_policy(self, user, facility):
        """
        Check if the user has permission to view immunization policies in the facility
        """
        return self.check_permission_in_facility_organization(
            [ImmunizationPermissions.can_write_immunization_policy.name],
            user,
            facility=facility,
            root=True,
        )


AuthorizationController.register_internal_controller(ImmunizationAccess)
