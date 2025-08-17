from care.security.authorization import AuthorizationController
from care.security.authorization.base import AuthorizationHandler
from care.security.permissions.invoice import InvoicePermissions


class InvoiceAccess(AuthorizationHandler):
    def can_write_invoice_in_facility(self, user, facility):
        return self.check_permission_in_facility_organization(
            [InvoicePermissions.can_write_invoice.name],
            user,
            facility=facility,
        )

    def can_read_invoice_in_facility(self, user, facility):
        return self.check_permission_in_facility_organization(
            [InvoicePermissions.can_read_invoice.name],
            user,
            facility=facility,
        )

    def can_destroy_invoice_in_facility(self, user, facility):
        return self.check_permission_in_facility_organization(
            [InvoicePermissions.can_destroy_invoice.name],
            user,
            facility=facility,
        )


AuthorizationController.register_internal_controller(InvoiceAccess)
