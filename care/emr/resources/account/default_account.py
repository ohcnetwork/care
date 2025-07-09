from care.emr.models.account import Account
from care.emr.resources.account.spec import (
    AccountBillingStatusOptions,
    AccountStatusOptions,
)
from care.utils.time_util import care_now


def get_default_account(patient, facility):
    account = Account.objects.filter(
        patient=patient,
        facility=facility,
        status=AccountStatusOptions.active.value,
        billing_status=AccountBillingStatusOptions.open.value,
    ).first()
    if account:
        return account
    return Account.objects.create(
        patient=patient,
        facility=facility,
        status=AccountStatusOptions.active.value,
        billing_status=AccountBillingStatusOptions.open.value,
        name=f"{patient.name} Default Account {care_now().strftime('%Y-%m-%d')}",
    )
