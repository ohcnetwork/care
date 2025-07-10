from care.security.authorization import AuthorizationController
from care.security.authorization.base import AuthorizationHandler
from care.security.permissions.specimen_definition import SpecimenDefinitionPermissions


class SpecimenDefinitionAccess(AuthorizationHandler):
    def can_list_facility_specimen_definition(self, user, facility):
        """
        Check if the user has permission to view observation definitions in the facility
        """
        return self.check_permission_in_facility_organization(
            [SpecimenDefinitionPermissions.can_read_specimen_definition.name],
            user,
            facility=facility,
        )

    def can_write_facility_specimen_definition(self, user, facility):
        """
        Check if the user has permission to view observation definitions in the facility
        """
        return self.check_permission_in_facility_organization(
            [SpecimenDefinitionPermissions.can_write_specimen_definition.name],
            user,
            facility=facility,
            root=True,
        )


AuthorizationController.register_internal_controller(SpecimenDefinitionAccess)
