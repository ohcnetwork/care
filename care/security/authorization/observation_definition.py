from care.security.authorization import AuthorizationController
from care.security.authorization.base import AuthorizationHandler
from care.security.permissions.observation_definition import (
    ObservationDefinitionPermissions,
)


class ObservationDefinitionAccess(AuthorizationHandler):
    def can_list_facility_observation_definition(self, user, facility):
        """
        Check if the user has permission to view observation definitions in the facility
        """
        return self.check_permission_in_facility_organization(
            [ObservationDefinitionPermissions.can_read_observation_definition.name],
            user,
            facility=facility,
        )

    def can_write_facility_observation_definition(self, user, facility):
        """
        Check if the user has permission to view observation definitions in the facility
        """
        return self.check_permission_in_facility_organization(
            [ObservationDefinitionPermissions.can_write_observation_definition.name],
            user,
            facility=facility,
            root=True,
        )


AuthorizationController.register_internal_controller(ObservationDefinitionAccess)
