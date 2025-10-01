from rest_framework.exceptions import ValidationError

from care.emr.locks.billing import InvoiceLock
from care.emr.resources.invoice.spec import InvoiceStatusOptions
from care.emr.resources.invoice.sync_items import sync_invoice_items


def handle_charge_item_cancel(charge_item):
    # Check if the charge item in an invoice and its in draft
    # Remove the charge item from the invoice
    # Rebalance the invoice
    if not charge_item.paid_invoice:
        return
    with InvoiceLock(charge_item.paid_invoice):
        if (
            charge_item.paid_invoice
            and charge_item.paid_invoice.status != InvoiceStatusOptions.draft.value
        ):
            raise ValidationError("Cannot cancel charge item in a non-draft invoice")
        if charge_item.paid_invoice:
            charge_item.paid_invoice.charge_items.remove(charge_item.id)
            sync_invoice_items(charge_item.paid_invoice)
            charge_item.paid_invoice.save()
            charge_item.paid_invoice = None
