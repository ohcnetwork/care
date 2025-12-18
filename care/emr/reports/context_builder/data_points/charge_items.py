from django_filters import rest_framework as filters

from care.emr.models.charge_item import ChargeItem
from care.emr.reports.context_builder.data_points.base import (
    Field,
    QuerysetContextBuilder,
)
from care.emr.reports.context_builder.data_points.monetary_component import (
    MonetaryComponentContextBuilder,
    UnitPriceMonetaryComponentContextBuilder,
)

CHARGE_ITEM_RESOURCE_DISPLAY = {
    "service_request": "Service Request",
    "medication_dispense": "Medication Dispense",
    "appointment": "Appointment",
    "bed_association": "Bed Association",
}
CHARGE_ITEM_STATUS_DISPLAY = {
    "planned": "Planned",
    "billable": "Billable",
    "not_billable": "Not Billable",
    "aborted": "Aborted",
    "billed": "Billed",
    "paid": "Paid",
    "entered_in_error": "Entered in Error",
}


class ChargeItemReportFilter(filters.FilterSet):
    status = filters.CharFilter(lookup_expr="iexact")
    title = filters.CharFilter(lookup_expr="icontains")
    service_resource = filters.CharFilter(lookup_expr="icontains")


class ChargeItemContextBuilder(QuerysetContextBuilder):
    filterset_class = ChargeItemReportFilter
    __filterset_backends__ = [filters.DjangoFilterBackend]

    title = Field(
        display="Charge Item Title",
        preview_value="General Consultation",
        description="Title of the charge item",
    )
    status = Field(
        display="Charge Item Status",
        preview_value="Active",
        mapping=lambda ci: CHARGE_ITEM_STATUS_DISPLAY.get(
            ci.status, ci.status.replace("_", " ").title()
        )
        if ci.status
        else "",
        description="Current status of the charge item",
    )
    service_resource = Field(
        display="Service Resource",
        preview_value="Consultation Service",
        mapping=lambda ci: CHARGE_ITEM_RESOURCE_DISPLAY.get(
            ci.service_resource, ci.service_resource.replace("_", " ").title()
        )
        if ci.service_resource
        else "",
        description="Service resource associated with the charge item",
    )
    quantity = Field(
        display="Quantity",
        preview_value="5",
        description="Quantity of the charge item",
    )
    unit_price_components = Field(
        display="Unit Price Components",
        preview_value="",
        target_context=UnitPriceMonetaryComponentContextBuilder,
        description="Unit price components of the charge item",
    )
    total_price = Field(
        display="Total Price",
        preview_value="100.00",
        description="Total price of the charge item",
    )
    total_price_components = Field(
        display="Total Price Components",
        preview_value="",
        target_context=MonetaryComponentContextBuilder,
        description="Breakdown of total price components of the charge item",
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
