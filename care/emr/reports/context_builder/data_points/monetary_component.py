from care.emr.reports.context_builder.data_points.base import (
    Field,
    QuerysetContextBuilder,
)

MONETARY_COMPONENT_TYPE_DISPLAY = {
    "base": "Base",
    "surcharge": "Surcharge",
    "discount": "Discount",
    "tax": "Tax",
    "informational": "Informational",
}


class MonetaryComponentContextBuilder(QuerysetContextBuilder):
    monetary_component_type = Field(
        display="Monetary Component Type",
        preview_value="Base",
        description="Type of the monetary component",
        mapping=lambda mc: MONETARY_COMPONENT_TYPE_DISPLAY.get(
            mc.monetary_component_type, mc.monetary_component_type.title()
        ),
    )
    code = Field(
        display="Code",
        preview_value="MRP",
        description="Coding representing the monetary component",
        mapping=lambda mc: mc.code.get("display", "") if mc.code else "",
    )
    factor = Field(
        display="Factor",
        preview_value="10.0",
        description="Factor applied to the base amount for this monetary component",
    )
    amount = Field(
        display="Amount",
        preview_value="100.00",
        description="Fixed amount for this monetary component",
    )

    def get_context(self):
        return self.parent_context.total_price_components


class UnitPriceMonetaryComponentContextBuilder(MonetaryComponentContextBuilder):
    def get_context(self):
        return self.parent_context.unit_price_components
