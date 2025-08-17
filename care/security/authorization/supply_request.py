from care.security.authorization import AuthorizationController
from care.security.authorization.base import AuthorizationHandler
from care.security.permissions.supply_request import SupplyRequestPermissions


class SupplyRequestAccess(AuthorizationHandler):
    def can_list_facility_supply_request(self, user, location):
        """
        Check if the user has permission to view supply requests in the location
        """
        return self.check_permission_in_facility_organization(
            [SupplyRequestPermissions.can_read_supply_request.name],
            user,
            orgs=location.facility_organization_cache,
        )

    def can_list_all_facility_supply_request(self, user, facility):
        """
        Check if the user has permission to view all supply requests in the facility
        """
        return self.check_permission_in_facility_organization(
            [SupplyRequestPermissions.can_read_supply_request.name],
            user,
            facility=facility,
            root=True,
        )

    def can_write_facility_supply_request(self, user, location):
        """
        Check if the user has permission to view supply requests in the location
        """
        return self.check_permission_in_facility_organization(
            [SupplyRequestPermissions.can_write_supply_request.name],
            user,
            orgs=location.facility_organization_cache,
        )


AuthorizationController.register_internal_controller(SupplyRequestAccess)
