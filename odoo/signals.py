from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from care.emr.models.charge_item_definition import ChargeItemDefinition
from care.emr.models.invoice import Invoice
from care.emr.models.organization import Organization
from care.emr.models.payment_reconciliation import PaymentReconciliation
from care.emr.models.resource_category import ResourceCategory
from care.emr.models.supply_delivery import DeliveryOrder
from care.emr.resources.inventory.supply_delivery.delivery_order import (
    SupplyDeliveryOrderStatusOptions,
)
from care.emr.resources.invoice.spec import (
    INVOICE_CANCELLED_STATUS,
    InvoiceStatusOptions,
)
from care.emr.resources.organization.spec import OrganizationTypeChoices
from care.emr.resources.payment_reconciliation.spec import (
    PaymentReconciliationStatusOptions,
)
from care.emr.resources.resource_category.spec import (
    ResourceCategoryResourceTypeOptions,
)
from care.users.models import User
from odoo.resource.account_move.delivery_order import OdooDeliveryOrderResource
from odoo.resource.account_move.invoice import OdooInvoiceResource
from odoo.resource.account_move_payment.payment import OdooPaymentResource
from odoo.resource.product_category.category import OdooCategoryResource
from odoo.resource.product_product.resource import OdooProductProductResource
from odoo.resource.res_partner.resource import OdooPartnerResource
from odoo.resource.res_user.resource import OdooUserResource


@receiver(post_save, sender=User)
def sync_user_to_odoo(sender, instance, created, **kwargs):
    """
    Signal handler to sync user to Odoo when created or updated.
    """
    with transaction.atomic():
        odoo_user = OdooUserResource()
        odoo_user.sync_user_to_odoo_api(instance)


@receiver(post_save, sender=Invoice)
def save_fields_before_update(sender, instance, raw, using, update_fields, **kwargs):
    if instance.status in [
        InvoiceStatusOptions.issued.value,
    ]:
        odoo_integration = OdooInvoiceResource()
        odoo_integration.sync_invoice_to_odoo_api(instance.external_id)
    elif instance.status in INVOICE_CANCELLED_STATUS:
        odoo_integration = OdooInvoiceResource()
        odoo_integration.sync_invoice_return_to_odoo_api(instance.external_id)


@receiver(post_save, sender=PaymentReconciliation)
def sync_payment_to_odoo(sender, instance, created, **kwargs):
    """
    Signal handler to sync payment reconciliation to Odoo when created.
    """
    if created:
        with transaction.atomic():
            if instance.status == PaymentReconciliationStatusOptions.active.value:
                odoo_payment = OdooPaymentResource()
                odoo_payment.sync_payment_to_odoo_api(instance.external_id)


@receiver(post_save, sender=ChargeItemDefinition)
def sync_charge_item_definition_to_odoo(sender, instance, created, **kwargs):
    """
    Signal handler to sync charge item definition to Odoo as a product when created or updated.
    """
    with transaction.atomic():
        odoo_product = OdooProductProductResource()
        odoo_product.sync_product_to_odoo_api(instance)


@receiver(post_save, sender=ResourceCategory)
def sync_resource_category_to_odoo(sender, instance, created, **kwargs):
    """
    Signal handler to sync resource category to Odoo when created or updated.
    """
    with transaction.atomic():
        if (
            instance.resource_type
            == ResourceCategoryResourceTypeOptions.charge_item_definition.value
        ):
            odoo_category = OdooCategoryResource()
            odoo_category.sync_category_to_odoo_api(instance)


@receiver(post_save, sender=Organization)
def sync_organization_to_odoo(sender, instance, created, **kwargs):
    """
    Signal handler to sync organization to Odoo as a partner when org_type is product_supplier.
    """
    if instance.org_type == OrganizationTypeChoices.product_supplier.value:
        with transaction.atomic():
            odoo_partner = OdooPartnerResource()
            odoo_partner.sync_partner_to_odoo_api(instance)


@receiver(post_save, sender=DeliveryOrder)
def sync_delivery_order_to_odoo(sender, instance, created, **kwargs):
    """
    Signal handler to sync delivery order to Odoo as a vendor bill when completed.
    """
    if instance.status == SupplyDeliveryOrderStatusOptions.completed.value:
        with transaction.atomic():
            odoo_delivery_order = OdooDeliveryOrderResource()
            odoo_delivery_order.sync_delivery_order_to_odoo_api(instance.external_id)
