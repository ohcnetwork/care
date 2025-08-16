from care.security.authorization import AuthorizationController
from care.security.authorization.base import AuthorizationHandler
from care.security.permissions.charge_item_definition import (
    ChargeItemDefinitionPermissions,
)


class ChargeItemDefinitionAccess(AuthorizationHandler):
    def can_list_facility_charge_item_definition(self, user, facility):
        """
        Check if the user has permission to view charge item definitions in the facility
        """
        return self.check_permission_in_facility_organization(
            [ChargeItemDefinitionPermissions.can_read_charge_item_definition.name],
            user,
            facility=facility,
        )

    def can_write_facility_charge_item_definition(self, user, facility):
        """
        Check if the user has permission to write charge item definitions in the facility
        """
        return self.check_permission_in_facility_organization(
            [ChargeItemDefinitionPermissions.can_write_charge_item_definition.name],
            user,
            facility=facility,
            root=True,
        )


AuthorizationController.register_internal_controller(ChargeItemDefinitionAccess)
