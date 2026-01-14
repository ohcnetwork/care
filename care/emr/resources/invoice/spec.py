import datetime
from decimal import Decimal
from enum import Enum

from pydantic import UUID4

from care.emr.models.account import Account
from care.emr.models.charge_item import ChargeItem
from care.emr.models.invoice import Invoice
from care.emr.models.payment_reconciliation import PaymentReconciliation
from care.emr.resources.account.spec import AccountMinimalReadSpec, AccountReadSpec
from care.emr.resources.base import EMRResource, model_from_cache
from care.emr.resources.charge_item.spec import ChargeItemReadSpec
from care.emr.resources.payment_reconciliation.spec import (
    PaymentReconciliationMinimalReadSpec,
)
from care.emr.resources.user.spec import UserSpec


class InvoiceStatusOptions(str, Enum):
    draft = "draft"
    issued = "issued"
    balanced = "balanced"
    cancelled = "cancelled"
    entered_in_error = "entered_in_error"


INVOICE_CANCELLED_STATUS = [
    InvoiceStatusOptions.cancelled.value,
    InvoiceStatusOptions.entered_in_error.value,
]


class BaseInvoiceSpec(EMRResource):
    """Base model for healthcare service"""

    __model__ = Invoice
    __exclude__ = ["account", "charge_items"]

    id: UUID4 | None = None
    title: str | None = None
    status: InvoiceStatusOptions
    cancelled_reason: str | None = None
    payment_terms: str | None = None
    note: str | None = None
    issue_date: datetime.datetime | None = None
    number: str | None = None


class InvoiceWriteSpec(BaseInvoiceSpec):
    """Invoice write specification"""

    account: UUID4
    charge_items: list[UUID4] = []

    def perform_extra_deserialization(self, is_update, obj):
        obj.account = Account.objects.get(external_id=self.account)
        obj.patient = obj.account.patient
        obj.charge_items = self.charge_items  # Rewritten in perform_create


class InvoiceReadSpec(BaseInvoiceSpec):
    """Invoice read specification"""

    total_net: Decimal
    total_gross: Decimal
    locked: bool
    created_date: datetime.datetime
    modified_date: datetime.datetime
    account: dict

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["account"] = AccountMinimalReadSpec.serialize(obj.account).to_json()
        if obj.locked:
            mapping["total_net"] = 0
            mapping["total_gross"] = 0


class InvoiceRetrieveSpec(InvoiceReadSpec):
    """Invoice retrieve specification"""

    charge_items: list[dict]
    total_price_components: list[dict]
    created_by: dict | None
    updated_by: dict | None
    payments: list[dict]
    total_payments: Decimal
    lock_history: list[dict]

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["account"] = AccountMinimalReadSpec.serialize(obj.account).to_json()
        if obj.status in (InvoiceStatusOptions.draft.value,):
            mapping["charge_items"] = [
                ChargeItemReadSpec.serialize(charge_item)
                for charge_item in ChargeItem.objects.filter(
                    id__in=obj.charge_items
                ).select_related("paid_invoice", "charge_item_definition")
            ]
        else:
            mapping["charge_items"] = obj.charge_items_copy
        mapping["account"] = AccountReadSpec.serialize(obj.account).to_json()
        cls.serialize_audit_users(mapping, obj)
        payments = []
        total_payments = Decimal(0)
        for payment in PaymentReconciliation.objects.filter(target_invoice=obj):
            payments.append(
                PaymentReconciliationMinimalReadSpec.serialize(payment).to_json()
            )
            total_payments += payment.amount
        mapping["total_payments"] = total_payments
        mapping["payments"] = payments
        lock_history = []
        for history in obj.lock_history:
            user = history.get("user")
            history["user"] = model_from_cache(UserSpec, id=user)
            lock_history.append(history)
        mapping["lock_history"] = lock_history
