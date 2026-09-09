from care.emr.reports.context_builder.data_points.base import (
    Field,
    QuerysetContextBuilder,
    SingleObjectContextBuilder,
)
from care.emr.reports.context_builder.data_points.charge_items import (
    SingleChargeItemContextBuilder,
)
from care.emr.reports.context_builder.data_points.schedule import (
    AvailabilityContextBuilder,
    ScheduleResourceContextBuilder,
)
from care.emr.reports.context_builder.data_points.token import TokenContextBuilder
from care.emr.reports.context_builder.data_points.user import (
    SingleUserRelatedContextBuilder,
)


class TokenSlotContextBuilder(SingleObjectContextBuilder):
    def get_context(self):
        return getattr(self.parent_context, self.parent_attribute)

    resource = Field(
        display="Resource",
        description="The resource associated with the token slot",
        target_context=ScheduleResourceContextBuilder,
    )
    availability = Field(
        display="Availability",
        description="The availability associated with the token slot",
        target_context=AvailabilityContextBuilder,
    )
    start_datetime = Field(
        display="Start DateTime",
        preview_value="2024-01-15T10:30:00Z",
        description="The start date and time of the token slot",
    )
    end_datetime = Field(
        display="End DateTime",
        preview_value="2024-01-15T11:00:00Z",
        description="The end date and time of the token slot",
    )


class TokenBookingContextFields:
    token_slot = Field(
        display="Token Slot",
        description="The token slot associated with the booking",
        target_context=TokenSlotContextBuilder,
    )
    status = Field(
        display="Status",
        description="The status of the booking",
    )
    booked_on = Field(
        display="Booked On",
        preview_value="2024-01-15T10:30:00Z",
        description="The date and time when the booking was made",
    )
    booked_by = Field(
        display="Booked By",
        description="The user who made the booking",
        target_context=SingleUserRelatedContextBuilder,
    )
    note = Field(
        display="Note",
        description="Any additional notes associated with the booking",
    )
    charge_item = Field(
        display="Charge Item",
        description="The charge item associated with the booking",
        target_context=SingleChargeItemContextBuilder,
    )
    token = Field(
        display="Token",
        description="The token associated with the booking",
        target_context=TokenContextBuilder,
    )


class TokenBookingContextBuilder(TokenBookingContextFields, QuerysetContextBuilder):
    pass


class SingleTokenBookingContextBuilder(
    TokenBookingContextFields, SingleObjectContextBuilder
):
    pass
