from care.emr.models.account import Account
from care.emr.reports.context_builder.data_point_registry import DataPointRegistry
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
from care.emr.reports.context_builder.data_points.monetary_component import (
    MonetaryComponentContextBuilder,
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


class AccountPatientContextBuilder(SingleObjectContextBuilder):
    def get_context(self):
        return self.parent_context.patient

    name = Field(
        display="Patient Name",
        preview_value="John Doe",
        description="Full name of the patient",
    )
    age = Field(
        display="Patient Age",
        mapping=lambda p: p.get_age(),
        preview_value="30 Y",
        description="Age of the patient",
    )

    gender = Field(
        display="Patient Gender",
        mapping=lambda p: p.gender,
        preview_value="Male",
        description="Gender of the patient",
    )


class BaseAccountContextBuilder(SingleObjectContextBuilder):
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
    total_price_components = Field(
        display="Total Price Components",
        preview_value="",
        target_context=MonetaryComponentContextBuilder,
        description="Breakdown of total price components for the account",
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


class PatientAccountContextBuilder(BaseAccountContextBuilder):
    def get_context(self):
        accounts = Account.objects.filter(patient=self.parent_context)
        return accounts.first()


class AccountContextBuilder(BaseAccountContextBuilder):
    standalone_context = True
    __slug__ = "account_base"
    __associating_model__ = Account
    __display_name__ = "Account Report"
    __description__ = "Report context for account-based reports"
    context_key = "account"

    patient = Field(
        display="Patient Details",
        target_context=AccountPatientContextBuilder,
        preview_value="",
        description="Details of the patient associated with the account",
    )


DataPointRegistry.register(AccountContextBuilder)
