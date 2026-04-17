from django_filters import rest_framework as filters

from care.emr.models.payment_reconciliation import PaymentReconciliation
from care.emr.reports.context_builder.data_points.base import (
    Field,
    QuerysetContextBuilder,
)
from care.emr.reports.context_builder.data_points.invoice import (
    MinimumInvoiceContextBuilder,
)

PAYMENT_RECONCILIATION_STATUS = {
    "active": "Active",
    "cancelled": "Cancelled",
    "draft": "Draft",
    "entered_in_error": "Entered in Error",
}

PAYMENT_RECONCILIATION_TYPE = {
    "payment": "Payment",
    "adjustment": "Adjustment",
    "advance": "Advance",
}
PAYMENT_RECONCILIATION_KIND = {
    "deposit": "Deposit",
    "periodic_payment": "Periodic Payment",
    "online": "Online",
    "kiosk": "Kiosk",
}
PAYMENT_RECONCILIATION_ISSUER_TYPE = {
    "patient": "Patient",
    "insurer": "Insurer",
}
PAYMENT_RECONCILIATION_OUTCOME = {
    "queued": "Queued",
    "complete": "Complete",
    "error": "Error",
    "partial": "Partial",
}
PAYMENT_RECONCILIATION_PAYMENT_METHOD = {
    "cash": "Cash",
    "ccca": "Credit Card",
    "cchk": "Credit Check",
    "cdac": "Credit Account",
    "chck": "Check",
    "ddpo": "Direct Deposit",
    "debc": "Debit Card",
}


class PaymentReconciliationReportFilter(filters.FilterSet):
    status = filters.CharFilter(lookup_expr="iexact")
    target_invoice = filters.UUIDFilter(field_name="target_invoice__external_id")
    reconciliation_type = filters.CharFilter(lookup_expr="iexact")
    is_credit_note = filters.BooleanFilter(field_name="is_credit_note")
    location = filters.UUIDFilter(field_name="location__external_id")


class PaymentReconciliationContextBuilder(QuerysetContextBuilder):
    filterset_class = PaymentReconciliationReportFilter
    __filterset_backends__ = [filters.DjangoFilterBackend]

    status = Field(
        display="Payment Reconciliation Status",
        preview_value="Active",
        mapping=lambda p: PAYMENT_RECONCILIATION_STATUS.get(p.status, p.status.title())
        if p.status
        else "",
        description="Status of the payment reconciliation",
    )
    reconciliation_type = Field(
        display="Reconciliation Type",
        preview_value="Payment",
        mapping=lambda p: PAYMENT_RECONCILIATION_TYPE.get(
            p.reconciliation_type, p.reconciliation_type.title()
        )
        if p.reconciliation_type
        else "",
        description="Type of the payment reconciliation",
    )
    amount = Field(
        display="Reconciled Amount",
        preview_value="150.00",
        description="Amount reconciled in the payment reconciliation",
    )
    reference_number = Field(
        display="Reference Number",
        preview_value="PR-1001",
        description="Unique reference number of the payment reconciliation",
    )
    kind = Field(
        display="Kind",
        preview_value="Credit",
        mapping=lambda p: PAYMENT_RECONCILIATION_KIND.get(p.kind, p.kind.title())
        if p.kind
        else "",
        description="Kind of payment reconciliation",
    )

    is_credit_note = Field(
        display="Is Credit Note",
        preview_value="False",
        description="Indicates if the reconciliation is a credit note",
    )
    issuer_type = Field(
        display="Issuer Type",
        preview_value="Patient",
        mapping=lambda p: PAYMENT_RECONCILIATION_ISSUER_TYPE.get(
            p.issuer_type, p.issuer_type.title()
        )
        if p.issuer_type
        else "",
        description="Type of the issuer for the payment reconciliation",
    )
    outcome = Field(
        display="Outcome",
        preview_value="Success",
        mapping=lambda p: PAYMENT_RECONCILIATION_OUTCOME.get(
            p.outcome, p.outcome.title()
        )
        if p.outcome
        else "",
        description="Outcome of the payment reconciliation process",
    )
    method = Field(
        display="Payment Method",
        preview_value="Credit Card",
        mapping=lambda p: PAYMENT_RECONCILIATION_PAYMENT_METHOD.get(
            p.method, p.method.title()
        )
        if p.method
        else "",
        description="Method used for the payment reconciliation",
    )
    target_invoice = Field(
        display="Target Invoice",
        target_context=MinimumInvoiceContextBuilder,
        preview_value="",
        description="Invoice associated with the payment reconciliation",
    )
    created_date = Field(
        display="Created Date",
        preview_value="2024-01-01T10:00:00Z",
        description="Timestamp when the payment reconciliation was created",
    )

    def get_context(self):
        return PaymentReconciliation.objects.filter(account=self.parent_context)
