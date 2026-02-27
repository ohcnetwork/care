import datetime
from decimal import Decimal
from enum import Enum

from pydantic import UUID4, Field

from care.emr.models.account import Account
from care.emr.models.charge_item import ChargeItem
from care.emr.models.invoice import Invoice
from care.emr.models.payment_reconciliation import PaymentReconciliation
from care.emr.resources.account.spec import AccountMinimalReadSpec, AccountReadSpec
from care.emr.resources.base import EMRResource, model_from_cache
from care.emr.resources.charge_item.spec import ChargeItemReadSpec
from care.emr.resources.payment_reconciliation.spec import (
    PaymentReconciliationOutcomeOptions,
    PaymentReconciliationRetrieveSpec,
    PaymentReconciliationStatusOptions,
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

    total_net: Decimal = Field(max_digits=20, decimal_places=6)
    total_gross: Decimal = Field(max_digits=20, decimal_places=6)
    locked: bool
    created_date: datetime.datetime
    modified_date: datetime.datetime
    account: dict
    is_refund: bool

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["account"] = AccountMinimalReadSpec.serialize(obj.account).to_json()
        if obj.locked:
            mapping["total_net"] = Decimal(0)
            mapping["total_gross"] = Decimal(0)


class InvoiceRetrieveSpec(InvoiceReadSpec):
    """Invoice retrieve specification"""

    charge_items: list[dict]
    total_price_components: list[dict]
    created_by: dict | None
    updated_by: dict | None
    payments: list[dict]
    total_payments: Decimal = Field(max_digits=20, decimal_places=6)
    credit_notes: list[dict]
    total_credit_notes: Decimal = Field(max_digits=20, decimal_places=6)
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
        credit_notes = []
        total_payments = Decimal(0)
        total_credit_notes = Decimal(0)
        for payment in PaymentReconciliation.objects.filter(
            target_invoice=obj,
            outcome=PaymentReconciliationOutcomeOptions.complete.value,
            status=PaymentReconciliationStatusOptions.active.value,
        ):
            if payment.is_credit_note:
                credit_notes.append(
                    PaymentReconciliationRetrieveSpec.serialize(payment).to_json()
                )
                total_credit_notes += payment.amount
            else:
                payments.append(
                    PaymentReconciliationRetrieveSpec.serialize(payment).to_json()
                )
                total_payments += payment.amount
        mapping["total_payments"] = total_payments
        mapping["payments"] = payments
        mapping["credit_notes"] = credit_notes
        mapping["total_credit_notes"] = total_credit_notes
        lock_history = []
        for history in obj.lock_history:
            user = history.get("user")
            history["user"] = model_from_cache(UserSpec, id=user)
            lock_history.append(history)
        mapping["lock_history"] = lock_history
