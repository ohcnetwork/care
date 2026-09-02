from care.emr.reports.context_builder.data_points.base import (
    Field,
    SingleObjectContextBuilder,
)
from care.emr.reports.context_builder.data_points.user import (
    SingleUserRelatedContextBuilder,
)

AVAILABILITY_SLOT_TYPE = {
    "open": "Open",
    "appointment": "Appointment",
    "closed": "Closed",
}

RESOURCE_TYPE_CHOICES = {
    "practitioner": "Practitioner",
    "location": "Location",
    "healthcare_service": "Healthcare Service",
}


class ScheduleResourceContextBuilder(SingleObjectContextBuilder):
    def get_context(self):
        return getattr(self.parent_context, self.parent_attribute)

    resource_type = Field(
        display="Resource Type",
        description="Type of the resource associated with the schedule",
        mapping=lambda r: RESOURCE_TYPE_CHOICES.get(
            r.resource_type, r.resource_type.replace("_", " ").title()
        ),
    )
    user = Field(
        display="User",
        description="The user associated with the schedule",
        target_context=SingleUserRelatedContextBuilder,
    )


class ScheduleContextBuilder(SingleObjectContextBuilder):
    def get_context(self):
        return getattr(self.parent_context, self.parent_attribute)

    name = Field(
        display="Name",
        description="Name of the schedule",
    )
    valid_from = Field(
        display="Valid From",
        preview_value="2024-01-15T10:30:00Z",
        description="Start date and time from which the schedule is valid",
    )
    valid_to = Field(
        display="Valid To",
        preview_value="2024-01-15T11:00:00Z",
        description="End date and time until which the schedule is valid",
    )
    revisit_allowed_days = Field(
        display="Revisit Allowed Days",
        description="Number of days allowed for a revisit",
    )


class AvailabilityContextBuilder(SingleObjectContextBuilder):
    def get_context(self):
        return getattr(self.parent_context, self.parent_attribute)

    name = Field(
        display="Name",
        description="Name of the availability",
    )
    slot_type = Field(
        display="Slot Type",
        description="Type of the slot (e.g., token, appointment)",
        mapping=lambda a: AVAILABILITY_SLOT_TYPE.get(
            a.slot_type, a.slot_type.replace("_", " ").title()
        ),
    )
    slot_size_in_minutes = Field(
        display="Slot Size (in minutes)",
        description="Size of the slot in minutes",
    )
    reason = Field(
        display="Reason",
        description="Reason for the availability",
    )
    schedule = Field(
        display="Schedule",
        description="The schedule associated with the availability",
        target_context=ScheduleContextBuilder,
    )
