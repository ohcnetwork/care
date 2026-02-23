from django_filters import rest_framework as filters

from care.emr.models.invoice import Invoice
from care.emr.reports.context_builder.data_points.base import (
    Field,
    QuerysetContextBuilder,
    SingleObjectContextBuilder,
)
from care.emr.reports.context_builder.data_points.monetary_component import (
    MonetaryComponentContextBuilder,
)

STATUS_DISPLAY = {
    "draft": "Draft",
    "issued": "Issued",
    "balanced": "Balanced",
    "cancelled": "Cancelled",
    "entered_in_error": "Entered in Error",
}


class InvoiceReportFilter(filters.FilterSet):
    status = filters.CharFilter(lookup_expr="iexact")
    title = filters.CharFilter(lookup_expr="icontains")
    number = filters.CharFilter(lookup_expr="icontains")


class InvoiceContextBuilder(QuerysetContextBuilder):
    filterset_class = InvoiceReportFilter
    __filterset_backends__ = [filters.DjangoFilterBackend]

    title = Field(
        display="Invoice Title",
        preview_value="Medical Services Invoice",
        description="Title of the invoice",
    )
    status = Field(
        display="Invoice Status",
        preview_value="Issued",
        mapping=lambda i: STATUS_DISPLAY.get(i.status, i.status.title())
        if i.status
        else "",
        description="Current status of the invoice",
    )
    number = Field(
        display="Invoice Number",
        preview_value="INV-1001",
        description="Unique number of the invoice",
    )
    total_net = Field(
        display="Total Net Amount",
        preview_value="150.00",
        description="Total net amount of the invoice",
    )
    total_gross = Field(
        display="Total Gross Amount",
        preview_value="180.00",
        description="Total gross amount of the invoice",
    )
    total_price_components = Field(
        display="Total Price Components",
        preview_value="",
        target_context=MonetaryComponentContextBuilder,
        description="Breakdown of total price components of the invoice",
    )

    def get_context(self):
        return Invoice.objects.filter(patient=self.parent_context)


class AccountInvoiceContextBuilder(InvoiceContextBuilder):
    def get_context(self):
        return Invoice.objects.filter(account=self.parent_context)


class MinimumInvoiceContextBuilder(SingleObjectContextBuilder):
    def get_context(self):
        return getattr(self.parent_context, self.parent_attribute)

    title = Field(
        display="Invoice Title",
        preview_value="Medical Services Invoice",
        description="Title of the invoice",
    )

    number = Field(
        display="Invoice Number",
        preview_value="INV-1001",
        description="Unique number of the invoice",
    )
