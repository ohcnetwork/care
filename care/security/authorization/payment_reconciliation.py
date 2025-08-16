from care.security.authorization import AuthorizationController
from care.security.authorization.base import AuthorizationHandler
from care.security.permissions.payment_reconciliation import (
    PaymentReconciliationPermissions,
)


class PaymentReconciliationAccess(AuthorizationHandler):
    def can_write_payment_reconciliation_in_facility(self, user, facility):
        return self.check_permission_in_facility_organization(
            [PaymentReconciliationPermissions.can_write_payment_reconciliation.name],
            user,
            facility=facility,
        )

    def can_read_payment_reconciliation_in_facility(self, user, facility):
        return self.check_permission_in_facility_organization(
            [PaymentReconciliationPermissions.can_read_payment_reconciliation.name],
            user,
            facility=facility,
        )

    def can_destroy_payment_reconciliation_in_facility(self, user, facility):
        return self.check_permission_in_facility_organization(
            [PaymentReconciliationPermissions.can_destroy_payment_reconciliation.name],
            user,
            facility=facility,
        )


AuthorizationController.register_internal_controller(PaymentReconciliationAccess)
