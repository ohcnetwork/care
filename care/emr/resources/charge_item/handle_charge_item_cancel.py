from rest_framework.exceptions import ValidationError

from care.emr.locks.billing import AccountLock, InvoiceLock
from care.emr.models.invoice import Invoice
from care.emr.resources.invoice.spec import InvoiceStatusOptions
from care.emr.resources.invoice.sync_items import sync_invoice_items
from care.utils.lock import ObjectLocked


def handle_charge_item_cancel(charge_item, *, account_locked=False):
    """Detach an item; callers must save it in the same outer transaction."""
    if account_locked:
        _remove_charge_item_from_invoice(charge_item)
        return

    account_id = charge_item.account_id
    with AccountLock(charge_item.account):
        # Service and inventory cancellation callers may hold an older snapshot.
        charge_item.refresh_from_db()
        if charge_item.account_id != account_id:
            raise ObjectLocked
        _remove_charge_item_from_invoice(charge_item)


def _remove_charge_item_from_invoice(charge_item):
    if not charge_item.paid_invoice_id:
        return

    invoice = Invoice.objects.get(id=charge_item.paid_invoice_id)
    with InvoiceLock(invoice):
        invoice.refresh_from_db()
        if invoice.status != InvoiceStatusOptions.draft.value:
            raise ValidationError("Cannot cancel charge item in a non-draft invoice")
        if charge_item.id not in invoice.charge_items:
            raise ValidationError("Charge item not found in invoice")
        invoice.charge_items.remove(charge_item.id)
        sync_invoice_items(invoice)
        invoice.save()
        charge_item.paid_invoice = None
        charge_item.paid_on = None
