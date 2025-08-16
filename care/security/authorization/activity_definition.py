from care.security.authorization.base import (
    AuthorizationController,
    AuthorizationHandler,
)
from care.security.permissions.activity_definition import ActivityDefinitionPermissions


class ActivityDefinitionAccess(AuthorizationHandler):
    def can_list_facility_activity_definition(self, user, facility):
        """
        Check if the user has permission to view Activity definitions in the facility
        """
        return self.check_permission_in_facility_organization(
            [ActivityDefinitionPermissions.can_read_activity_definition.name],
            user,
            facility=facility,
        )

    def can_write_facility_activity_definition(self, user, facility):
        """
        Check if the user has permission to view observation definitions in the facility
        """
        return self.check_permission_in_facility_organization(
            [ActivityDefinitionPermissions.can_write_activity_definition.name],
            user,
            facility=facility,
            root=True,
        )


AuthorizationController.register_internal_controller(ActivityDefinitionAccess)
