from care.security.authorization import AuthorizationController
from care.security.authorization.base import AuthorizationHandler
from care.security.permissions.inventory_item import InventoryItemPermissions


class InventoryItemAccess(AuthorizationHandler):
    def can_list_location_inventory_item(self, user, location):
        """
        Check if the user has permission to view inventory items in the location
        """
        return self.check_permission_in_facility_organization(
            [InventoryItemPermissions.can_read_inventory_item.name],
            user,
            orgs=location.facility_organization_cache,
        )


AuthorizationController.register_internal_controller(InventoryItemAccess)
