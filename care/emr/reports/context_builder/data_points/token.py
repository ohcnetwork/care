from care.emr.reports.context_builder.data_points.base import (
    Field,
    SingleObjectContextBuilder,
)

RESOURCE_CATEGORY_RESOURCE_TYPE = {
    "product_knowledge": "Product Knowledge",
    "activity_definition": "Activity Definition",
    "charge_item_definition": "Charge Item Definition",
}


class TokenCategoryContextBuilder(SingleObjectContextBuilder):
    def get_context(self):
        return getattr(self.parent_context, self.parent_attribute)

    name = Field(
        display="Name",
        description="Name of the token category",
    )
    resource_type = Field(
        display="Resource Type",
        description="Type of the resource associated with the token category",
        mapping=lambda rc: RESOURCE_CATEGORY_RESOURCE_TYPE.get(
            rc.resource_type, rc.resource_type.replace("_", " ").title()
        ),
    )
    shorthand = Field(
        display="Shorthand",
        description="Shorthand representation of the token category",
    )


class TokenContextBuilder(SingleObjectContextBuilder):
    def get_context(self):
        return getattr(self.parent_context, self.parent_attribute)

    number = Field(
        display="Token Number",
        description="The token number associated with the booking",
    )
    status = Field(
        display="Status",
        description="The status of the token",
    )
    note = Field(
        display="Note",
        description="Any additional notes associated with the token",
    )
    category = Field(
        display="Token category",
        description="The category associated with the token",
        target_context=TokenCategoryContextBuilder,
    )
