from care.security.authorization.base import (
    AuthorizationController,
    AuthorizationHandler,
)
from care.security.permissions.healthcare_service import HealthcareServicePermissions


class HealthcareServiceAccess(AuthorizationHandler):
    def can_list_facility_healthcare_service(self, user, facility):
        """
        Check if the user has permission to view healthcare services in the facility
        """
        return self.check_permission_in_facility_organization(
            [HealthcareServicePermissions.can_read_healthcare_service.name],
            user,
            facility=facility,
        )

    def can_write_facility_healthcare_service(self, user, facility):
        """
        Check if the user has permission to view healthcare services in the facility
        """
        return self.check_permission_in_facility_organization(
            [HealthcareServicePermissions.can_write_healthcare_service.name],
            user,
            facility=facility,
            root=True,
        )


AuthorizationController.register_internal_controller(HealthcareServiceAccess)
