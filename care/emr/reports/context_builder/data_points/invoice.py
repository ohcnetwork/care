from django_filters import rest_framework as filters

from care.emr.models.invoice import Invoice
from care.emr.reports.context_builder.data_points.base import (
    Field,
    QuerysetContextBuilder,
)


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
        preview_value="Paid",
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

    def get_context(self):
        return Invoice.objects.filter(account=self.parent_context)
