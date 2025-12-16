from django_filters import rest_framework as filters

from care.emr.models.charge_item import ChargeItem
from care.emr.reports.context_builder.data_points.base import (
    Field,
    QuerysetContextBuilder,
)


class ChargeItemReportFilter(filters.FilterSet):
    status = filters.CharFilter(lookup_expr="iexact")
    title = filters.CharFilter(lookup_expr="icontains")
    service_resource = filters.CharFilter(lookup_expr="icontains")


class ChargeItemContextBuilder(QuerysetContextBuilder):
    filterset_class = ChargeItemReportFilter
    __filterset_backends__ = [filters.DjangoFilterBackend]

    status = Field(
        display="Charge Item Status",
        preview_value="Active",
        description="Current status of the charge item",
    )
    title = Field(
        display="Charge Item Title",
        preview_value="General Consultation",
        description="Title of the charge item",
    )
    service_resource = Field(
        display="Service Resource",
        preview_value="Consultation Service",
        description="Service resource associated with the charge item",
    )
    total_price = Field(
        display="Total Price",
        preview_value="100.00",
        description="Total price of the charge item",
    )
    paid_on = Field(
        display="Paid On",
        preview_value="2024-01-15T10:30:00Z",
        description="Date and time when the charge item was paid",
    )

    def get_context(self):
        return ChargeItem.objects.filter(patient=self.parent_context)


class AccountChargeItemContextBuilder(ChargeItemContextBuilder):
    def get_context(self):
        return ChargeItem.objects.filter(account=self.parent_context)
