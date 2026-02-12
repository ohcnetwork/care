from care.emr.models.account import Account
from care.emr.reports.authorizers.base import BaseReportAuthorizer
from care.security.authorization.base import AuthorizationController
from care.utils.shortcuts import get_object_or_404


class AccountReportAuthorizer(BaseReportAuthorizer):
    def authorize_read(self, user, associating_id: str) -> bool:
        account_obj = get_object_or_404(Account, external_id=associating_id)
        return AuthorizationController.call(
            "can_read_account_in_facility", user, account_obj.facility
        )

    def authorize_write(self, user, associating_id: str) -> bool:
        account_obj = get_object_or_404(Account, external_id=associating_id)
        return AuthorizationController.call(
            "can_update_account_in_facility", user, account_obj.facility
        )
