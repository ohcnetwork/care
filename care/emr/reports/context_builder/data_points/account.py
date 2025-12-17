from django_filters import rest_framework as filters

from care.emr.models.account import Account
from care.emr.reports.context_builder.data_points.base import (
    Field,
    SingleObjectContextBuilder,
)
from care.emr.reports.context_builder.data_points.charge_items import (
    AccountChargeItemContextBuilder,
)
from care.emr.reports.context_builder.data_points.invoice import (
    AccountInvoiceContextBuilder,
)
from care.emr.reports.context_builder.data_points.payment_reconciliation import (
    PaymentReconciliationContextBuilder,
)

STATUS_DISPLAY = {
    "active": "Active",
    "inactive": "Inactive",
    "entered_in_error": "Entered in Error",
    "on_hold": "On Hold",
}
BILLING_STATUS_DISPLAY = {
    "open": "Open",
    "carecomplete_notbilled": "CareComplete Not Billed",
    "billing": "Billing",
    "closed_baddebt": "Closed Bad Debt",
    "closed_voided": "Closed Voided",
    "closed_completed": "Closed Completed",
    "closed_combined": "Closed Combined",
}


class AccountReportFilter(filters.FilterSet):
    status = filters.CharFilter(lookup_expr="iexact")
    name = filters.CharFilter(lookup_expr="icontains")
    billing_status = filters.CharFilter(lookup_expr="iexact")
    created_date = filters.DateTimeFromToRangeFilter(field_name="created_date")


class AccountContextBuilder(SingleObjectContextBuilder):
    filterset_class = AccountReportFilter
    __filterset_backends__ = [filters.DjangoFilterBackend]

    name = Field(
        display="Account Title",
        preview_value="General Checkup Account",
        description="Title of the account",
    )
    status = Field(
        display="Account Status",
        preview_value="Active",
        mapping=lambda a: STATUS_DISPLAY.get(a.status, a.status.title())
        if a.status
        else "",
        description="Current status of the account",
    )
    billing_status = Field(
        display="Account Billing Status",
        preview_value="Billed",
        mapping=lambda a: BILLING_STATUS_DISPLAY.get(
            a.billing_status, a.billing_status.title()
        )
        if a.billing_status
        else "",
        description="Billing status of the account",
    )
    description = Field(
        display="Account Description",
        preview_value="Account for general health checkup",
        description="Detailed description of the account",
    )
    total_net = Field(
        display="Total Net Amount",
        preview_value="150.00",
        description="Total net amount for the account",
    )
    total_gross = Field(
        display="Total Gross Amount",
        preview_value="180.00",
        description="Total gross amount for the account",
    )
    total_paid = Field(
        display="Total Paid Amount",
        preview_value="100.00",
        description="Total amount paid towards the account",
    )
    total_balance = Field(
        display="Total Balance Amount",
        preview_value="80.00",
        description="Total balance amount remaining for the account",
    )
    invoices = Field(
        display="Associated Invoices",
        preview_value="",
        target_context=AccountInvoiceContextBuilder,
        description="Invoices linked to the account",
    )
    charge_items = Field(
        display="Billable Charge Items",
        preview_value="",
        target_context=AccountChargeItemContextBuilder,
        description="Chargeable items associated with the account",
    )
    payment_reconciliations = Field(
        display="Payment Reconciliations",
        preview_value="",
        target_context=PaymentReconciliationContextBuilder,
        description="Payment reconciliations for the account",
    )
    created_date = Field(
        display="Account Created Date",
        preview_value="2023-01-15T10:30:00Z",
        description="Date when the account was created",
    )
    calculated_at = Field(
        display="Account Calculated At",
        preview_value="2023-01-20T15:45:00Z",
        description="Date when the account totals were last calculated",
    )

    def get_context(self):
        accounts = Account.objects.filter(patient=self.parent_context)
        return accounts.first()
