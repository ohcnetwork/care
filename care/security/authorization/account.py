from care.security.authorization.base import (
    AuthorizationController,
    AuthorizationHandler,
)
from care.security.permissions.account import AccountPermissions


class AccountAccess(AuthorizationHandler):
    def can_create_account_in_facility(self, user, facility):
        return self.check_permission_in_facility_organization(
            [AccountPermissions.can_create_account.name],
            user,
            facility=facility,
        )

    def can_update_account_in_facility(self, user, facility):
        return self.check_permission_in_facility_organization(
            [AccountPermissions.can_update_account.name],
            user,
            facility=facility,
        )

    def can_read_account_in_facility(self, user, facility):
        return self.check_permission_in_facility_organization(
            [AccountPermissions.can_read_account.name],
            user,
            facility=facility,
        )


AuthorizationController.register_internal_controller(AccountAccess)
