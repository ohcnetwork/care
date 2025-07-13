from care.security.authorization.base import (
    AuthorizationController,
    AuthorizationHandler,
)
from care.security.permissions.medication import MedicationPermissions


class MedicationAccess(AuthorizationHandler):
    def can_list_location_medication_dispense(self, user, location):
        """
        Check if the user has permission to view healthcare services in the facility
        """
        return self.check_permission_in_facility_organization(
            [MedicationPermissions.read_medication_dispense.name],
            user,
            orgs=location.facility_organization_cache,
        )

    def can_write_location_medication_dispense(self, user, location):
        """
        Check if the user has permission to view healthcare services in the facility
        """
        return self.check_permission_in_facility_organization(
            [MedicationPermissions.write_medication_dispense.name],
            user,
            orgs=location.facility_organization_cache,
        )


AuthorizationController.register_internal_controller(MedicationAccess)
