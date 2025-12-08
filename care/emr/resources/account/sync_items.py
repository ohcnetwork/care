import json
from decimal import Decimal

from django.core.serializers.json import DjangoJSONEncoder

from care.emr.locks.billing import AccountLock
from care.emr.models.account import Account
from care.emr.models.charge_item import ChargeItem
from care.emr.models.payment_reconciliation import PaymentReconciliation
from care.emr.resources.charge_item.spec import ChargeItemStatusOptions
from care.emr.resources.invoice.sync_items import calculate_charge_items_summary
from care.emr.resources.payment_reconciliation.spec import (
    PaymentReconciliationOutcomeOptions,
    PaymentReconciliationStatusOptions,
)
from care.utils.time_util import care_now
from config.celery_app import app


def calculate_payment_reconciliation_summary(payment_reconciliations):
    total_paid = Decimal(0)
    for payment_reconciliation in payment_reconciliations:
        total_paid += Decimal(payment_reconciliation.amount)
    return total_paid


def sync_account_items(account: Account):
    with AccountLock(account):
        charge_items = ChargeItem.objects.filter(
            account=account,
            status__in=[
                ChargeItemStatusOptions.paid.value,
                ChargeItemStatusOptions.billed.value,
            ],
        )

        payment_reconciliations = PaymentReconciliation.objects.filter(
            account=account,
            status=PaymentReconciliationStatusOptions.active.value,
            outcome=PaymentReconciliationOutcomeOptions.complete.value,
            is_credit_note=False,
        )
        credit_note_payment_reconciliations = PaymentReconciliation.objects.filter(
            account=account,
            status=PaymentReconciliationStatusOptions.active.value,
            outcome=PaymentReconciliationOutcomeOptions.complete.value,
            is_credit_note=True,
        )
        charge_items_summary = calculate_charge_items_summary(charge_items)

        payment_reconciliation_total = calculate_payment_reconciliation_summary(
            payment_reconciliations
        )
        credit_note_payment_reconciliation_total = (
            calculate_payment_reconciliation_summary(
                credit_note_payment_reconciliations
            )
        )
        account.cached_items = charge_items_summary["charge_items_copy"]
        account.total_net = charge_items_summary["net"]
        account.total_gross = charge_items_summary["gross"]
        account.total_paid = (
            payment_reconciliation_total - credit_note_payment_reconciliation_total
        )
        account.total_balance = account.total_gross - account.total_paid
        account.total_price_components = json.loads(
            json.dumps(
                charge_items_summary["total_price_components"],
                cls=DjangoJSONEncoder,
            )
        )
        account.calculated_at = care_now()


@app.task()
def rebalance_account_task(account_id):
    account = Account.objects.get(id=account_id)
    sync_account_items(account)
    account.save()
