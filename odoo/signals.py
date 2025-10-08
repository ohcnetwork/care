from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction, IntegrityError

from care.emr.models.invoice import Invoice
from care.emr.resources.invoice.spec import InvoiceStatusOptions
from care.users.models import User
from odoo.resource.invoice import OdooInvoiceResource
from odoo.resource.agent import OdooAgentResource


@receiver(post_save, sender=User)
def create_odoo_agent(sender, instance, created, **kwargs):
    try:
        with transaction.atomic():
            agent_resource = OdooAgentResource()
            agent_resource.get_or_create_doctor_agent(instance)
    except Exception as e:
        raise IntegrityError("User creation failed due to Odoo agent creation error.") from e


@receiver(post_save, sender=Invoice)
def save_fields_before_update(sender, instance, raw, using, update_fields, **kwargs):
    if instance.status in [
        InvoiceStatusOptions.issued.value,
        InvoiceStatusOptions.balanced.value,
    ]:
        odoo_integration = OdooInvoiceResource()
        odoo_integration.sync_invoice_to_odoo_api(instance.external_id)
