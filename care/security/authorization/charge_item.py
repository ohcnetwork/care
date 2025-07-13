from care.security.authorization import AuthorizationController
from care.security.authorization.base import AuthorizationHandler
from care.security.permissions.charge_item import ChargeItemPermissions


class ChargeItemAccess(AuthorizationHandler):
    def can_create_charge_item_in_facility(self, user, facility):
        return self.check_permission_in_facility_organization(
            [ChargeItemPermissions.can_create_charge_item.name],
            user,
            facility=facility,
        )

    def can_update_charge_item_in_facility(self, user, facility):
        return self.check_permission_in_facility_organization(
            [ChargeItemPermissions.can_update_charge_item.name],
            user,
            facility=facility,
        )

    def can_read_charge_item_in_facility(self, user, facility):
        return self.check_permission_in_facility_organization(
            [ChargeItemPermissions.can_read_charge_item.name],
            user,
            facility=facility,
        )


AuthorizationController.register_internal_controller(ChargeItemAccess)
