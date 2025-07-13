from care.security.authorization import AuthorizationController
from care.security.authorization.base import AuthorizationHandler
from care.security.permissions.supply_delivery import SupplyDeliveryPermissions


class SupplyDeliveryAccess(AuthorizationHandler):
    def can_list_facility_supply_delivery(self, user, location):
        """
        Check if the user has permission to view supply deliveries in the location
        """
        return self.check_permission_in_facility_organization(
            [SupplyDeliveryPermissions.can_read_supply_delivery.name],
            user,
            orgs=location.facility_organization_cache,
        )

    def can_write_facility_supply_delivery(self, user, location):
        """
        Check if the user has permission to view supply deliveries in the location
        """
        return self.check_permission_in_facility_organization(
            [SupplyDeliveryPermissions.can_write_supply_delivery.name],
            user,
            orgs=location.facility_organization_cache,
        )


AuthorizationController.register_internal_controller(SupplyDeliveryAccess)
