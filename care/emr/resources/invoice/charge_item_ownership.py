from rest_framework.exceptions import ValidationError

from care.emr.models.charge_item import ChargeItem
from care.emr.resources.charge_item.spec import ChargeItemStatusOptions


def validate_charge_item_ownership(charge_items, invoice=None):
    """Check the owning invoice while holding the account lock."""
    invoice_id = invoice.pk if invoice else None
    if any(
        item.paid_invoice_id is not None and item.paid_invoice_id != invoice_id
        for item in charge_items
    ):
        raise ValidationError("Charge item already belongs to another invoice")


def validate_invoice_charge_items(invoice):
    charge_items = list(ChargeItem.objects.filter(pk__in=invoice.charge_items))
    if len(charge_items) != len(invoice.charge_items) or any(
        item.account_id != invoice.account_id
        or item.paid_invoice_id != invoice.pk
        or item.status != ChargeItemStatusOptions.billed.value
        for item in charge_items
    ):
        raise ValidationError("Invoice contains charge items that it does not own")
