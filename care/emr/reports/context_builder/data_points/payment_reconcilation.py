from django_filters import rest_framework as filters

from care.emr.models.payment_reconciliation import PaymentReconciliation
from care.emr.reports.context_builder.data_points.base import (
    Field,
    QuerysetContextBuilder,
)


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
        preview_value="Completed",
        description="Current status of the payment reconciliation",
    )
    reconciliation_type = Field(
        display="Reconciliation Type",
        preview_value="Payment",
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
        description="Type of the issuer for the payment reconciliation",
    )
    outcome = Field(
        display="Outcome",
        preview_value="Success",
        description="Outcome of the payment reconciliation process",
    )
    method = Field(
        display="Payment Method",
        preview_value="Credit Card",
        description="Method used for the payment reconciliation",
    )

    def get_context(self):
        return PaymentReconciliation.objects.filter(account=self.parent_context)
