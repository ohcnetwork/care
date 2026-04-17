"""
Utilities to create a return invoice for items based on delivery order
"""

from django.db import transaction
from rest_framework.exceptions import ValidationError

from care.emr.models.charge_item import ChargeItem
from care.emr.models.invoice import Invoice
from care.emr.models.supply_delivery import DeliveryOrder, SupplyDelivery
from care.emr.resources.account.default_account import get_default_account
from care.emr.resources.account.sync_items import rebalance_account_task
from care.emr.resources.charge_item.apply_charge_item_definition import (
    apply_charge_item_definition,
)
from care.emr.resources.charge_item.spec import ChargeItemStatusOptions
from care.emr.resources.inventory.inventory_item.sync_inventory_item import (
    sync_inventory_item,
)
from care.emr.resources.inventory.supply_delivery.spec import (
    SupplyDeliveryStatusOptions,
)
from care.emr.resources.invoice.default_expression_evaluator import (
    evaluate_invoice_identifier_default_expression,
)
from care.emr.resources.invoice.spec import InvoiceStatusOptions
from care.emr.resources.invoice.sync_items import sync_invoice_items
from care.utils.time_util import care_now


def generate_return_invoice(delivery_order: DeliveryOrder):
    """
    Generate a return invoice for items based on delivery order
    """

    with transaction.atomic():
        charge_items = []
        if SupplyDelivery.objects.filter(
            order=delivery_order, status=SupplyDeliveryStatusOptions.in_progress.value
        ).exists():
            raise ValidationError("Finalise Deliveries before completing order")
        invoice_obj = Invoice()
        invoice_obj.status = InvoiceStatusOptions.draft.value
        invoice_obj.facility = delivery_order.destination.facility
        invoice_obj.account = get_default_account(
            delivery_order.patient, invoice_obj.facility
        )
        invoice_obj.number = evaluate_invoice_identifier_default_expression(
            invoice_obj.facility
        )
        invoice_obj.patient = delivery_order.patient
        invoice_obj.is_refund = True
        invoice_obj.issue_date = care_now()
        invoice_obj.created_by = delivery_order.created_by
        invoice_obj.updated_by = delivery_order.updated_by
        invoice_obj.save()
        for supply_delivery in SupplyDelivery.objects.filter(
            order=delivery_order, status=SupplyDeliveryStatusOptions.completed.value
        ):
            product = supply_delivery.supplied_item
            charge_item_definition = product.charge_item_definition
            if not charge_item_definition:
                continue
            charge_item = apply_charge_item_definition(
                charge_item_definition,
                delivery_order.patient,
                delivery_order.destination.facility,
                reverse=True,
                quantity=supply_delivery.supplied_item_quantity,
            )
            charge_item.status = ChargeItemStatusOptions.billed.value
            charge_item.paid_invoice = invoice_obj
            charge_item.created_by = delivery_order.created_by
            charge_item.updated_by = delivery_order.updated_by
            charge_item.save()
            charge_items.append(charge_item.id)
        invoice_obj.charge_items = charge_items
        sync_invoice_items(invoice_obj)
        invoice_obj.status = InvoiceStatusOptions.issued.value
        invoice_obj.save()
        delivery_order.patient_invoice = invoice_obj
        delivery_order.save(update_fields=["patient_invoice"])
    rebalance_account_task(invoice_obj.account.id)
    return invoice_obj


def cancel_return_invoice(delivery_order: DeliveryOrder):
    """
    Cancel the return invoice for items based on delivery order
    """
    if not delivery_order.patient_invoice:
        return
    with transaction.atomic():
        delivery_order.patient_invoice.status = InvoiceStatusOptions.cancelled.value
        delivery_order.patient_invoice.updated_by = delivery_order.updated_by
        delivery_order.patient_invoice.save(update_fields=["status", "updated_by"])
        ChargeItem.objects.filter(
            id__in=delivery_order.patient_invoice.charge_items,
        ).update(
            status=ChargeItemStatusOptions.entered_in_error.value,
            paid_invoice=None,
            paid_on=None,
        )
        supply_deliveries = SupplyDelivery.objects.filter(order=delivery_order)
        for supply_delivery in supply_deliveries:
            sync_inventory_item(
                location=delivery_order.destination,
                product=supply_delivery.supplied_item,
            )

    rebalance_account_task(delivery_order.patient_invoice.account.id)
