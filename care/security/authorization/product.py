from care.security.authorization import AuthorizationController
from care.security.authorization.base import AuthorizationHandler
from care.security.permissions.product import ProductPermissions


class ProductAccess(AuthorizationHandler):
    def can_list_facility_product(self, user, facility):
        """
        Check if the user has permission to view products in the facility
        """
        return self.check_permission_in_facility_organization(
            [ProductPermissions.can_read_product.name],
            user,
            facility=facility,
        )

    def can_write_facility_product(self, user, facility):
        """
        Check if the user has permission to view products in the facility
        """
        return self.check_permission_in_facility_organization(
            [ProductPermissions.can_write_product.name],
            user,
            facility=facility,
            root=True,
        )


AuthorizationController.register_internal_controller(ProductAccess)
