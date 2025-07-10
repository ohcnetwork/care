from care.security.authorization import AuthorizationController
from care.security.authorization.base import AuthorizationHandler
from care.security.permissions.patient_identifier_config import (
    PatientIdentifierConfigPermissions,
)


class PatientIdentifierConfigAccess(AuthorizationHandler):
    def can_list_facility_patient_identifier_config(self, user, facility):
        """
        Check if the user has permission to view patient identifier configs in the facility
        """
        return self.check_permission_in_facility_organization(
            [
                PatientIdentifierConfigPermissions.can_read_patient_identifier_config.name
            ],
            user,
            facility=facility,
        )

    def can_write_facility_patient_identifier_config(self, user, facility):
        """
        Check if the user has permission to view patient identifier configs in the facility
        """
        return self.check_permission_in_facility_organization(
            [
                PatientIdentifierConfigPermissions.can_write_patient_identifier_config.name
            ],
            user,
            facility=facility,
            root=True,
        )


AuthorizationController.register_internal_controller(PatientIdentifierConfigAccess)
