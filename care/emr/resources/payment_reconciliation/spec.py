from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import UUID4, Field, model_validator

from care.emr.extensions.base import ExtensionResource
from care.emr.extensions.validator import ExtensionValidator
from care.emr.models.account import Account
from care.emr.models.invoice import Invoice
from care.emr.models.location import FacilityLocation
from care.emr.models.payment_reconciliation import PaymentReconciliation
from care.emr.resources.account.spec import AccountReadSpec
from care.emr.resources.base import EMRResource
from care.emr.resources.location.spec import FacilityLocationListSpec
from care.emr.resources.patient.spec import PatientRetrieveSpec


class PaymentReconciliationTypeOptions(str, Enum):
    payment = "payment"
    adjustment = "adjustment"
    advance = "advance"


class PaymentReconciliationStatusOptions(str, Enum):
    active = "active"
    cancelled = "cancelled"
    draft = "draft"
    entered_in_error = "entered_in_error"


class PaymentReconciliationKindOptions(str, Enum):
    deposit = "deposit"
    periodic_payment = "periodic_payment"
    online = "online"
    kiosk = "kiosk"


class PaymentReconciliationIssuerTypeOptions(str, Enum):
    patient = "patient"
    insurer = "insurer"


class PaymentReconciliationOutcomeOptions(str, Enum):
    queued = "queued"
    complete = "complete"
    error = "error"
    partial = "partial"


class PaymentReconciliationPaymentMethodOptions(str, Enum):
    cash = "cash"
    ccca = "ccca"
    cchk = "cchk"
    cdac = "cdac"
    chck = "chck"
    ddpo = "ddpo"
    debc = "debc"


class BasePaymentReconciliationSpec(EMRResource):
    """Base model for healthcare service"""

    __model__ = PaymentReconciliation
    __exclude__ = ["target_invoice", "account"]
    ___extension_resource_type__ = ExtensionResource.payment_reconciliation

    id: UUID4 | None = None
    reconciliation_type: PaymentReconciliationTypeOptions
    status: PaymentReconciliationStatusOptions
    kind: PaymentReconciliationKindOptions
    issuer_type: PaymentReconciliationIssuerTypeOptions
    outcome: PaymentReconciliationOutcomeOptions
    disposition: str | None = None
    payment_datetime: datetime | None = None
    method: PaymentReconciliationPaymentMethodOptions
    reference_number: str | None = None
    authorization: str | None = None

    note: str | None = None


class PaymentReconciliationWriteSpec(ExtensionValidator, BasePaymentReconciliationSpec):
    """Payment reconciliation write specification"""

    target_invoice: UUID4 | None = None
    account: UUID4
    amount: Decimal | None = Field(default=None, max_digits=20, decimal_places=6)
    tendered_amount: Decimal = Field(max_digits=20, decimal_places=6)
    returned_amount: Decimal = Field(max_digits=20, decimal_places=6)
    is_credit_note: bool = False
    location: UUID4 | None = None

    def perform_extra_deserialization(self, is_update, obj):
        if self.target_invoice:
            obj.target_invoice = Invoice.objects.get(external_id=self.target_invoice)
        obj.account = Account.objects.get(external_id=self.account)
        if self.location:
            obj.location = FacilityLocation.objects.get(external_id=self.location)

    @model_validator(mode="after")
    def check_amount_or_factor(self):
        if self.returned_amount >= self.tendered_amount:
            raise ValueError("Returned amount cannot be greater than tendered amount")
        self.amount = self.tendered_amount - self.returned_amount
        return self


class PaymentReconciliationMinimalReadSpec(BasePaymentReconciliationSpec):
    amount: Decimal | None = Field(default=None, max_digits=20, decimal_places=6)
    tendered_amount: Decimal = Field(max_digits=20, decimal_places=6)
    returned_amount: Decimal = Field(max_digits=20, decimal_places=6)
    is_credit_note: bool
    created_date: datetime
    modified_date: datetime

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id


class PaymentReconciliationReadSpec(PaymentReconciliationMinimalReadSpec):
    """Invoice read specification"""

    account: dict
    target_invoice: dict | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        from care.emr.resources.invoice.spec import InvoiceReadSpec

        super().perform_extra_serialization(mapping, obj)
        mapping["account"] = AccountReadSpec.serialize(obj.account).to_json()
        if obj.target_invoice:
            mapping["target_invoice"] = InvoiceReadSpec.serialize(
                obj.target_invoice
            ).to_json()


class PaymentReconciliationRetrieveSpec(PaymentReconciliationReadSpec):
    location: dict | None = None
    extensions: dict

    created_by: dict | None
    updated_by: dict | None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        mapping["account"]["patient"] = PatientRetrieveSpec.serialize(
            obj.account.patient, facility=obj.account.facility
        ).to_json()
        if obj.location:
            mapping["location"] = FacilityLocationListSpec.serialize(
                obj.location
            ).to_json()
        cls.serialize_audit_users(mapping, obj)
