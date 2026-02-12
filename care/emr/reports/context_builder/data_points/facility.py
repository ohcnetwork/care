from care.emr.reports.context_builder.data_points.base import (
    Field,
    SingleObjectContextBuilder,
)


class FacilityContextBuilder(SingleObjectContextBuilder):
    def get_context(self):
        return getattr(self.parent_context, self.parent_attribute)

    name = Field(
        display="Facility Name",
        preview_value="City Health Center",
        description="Name of the healthcare facility",
    )
    description = Field(
        display="Facility Description",
        preview_value="A community healthcare center providing primary care services.",
        description="Description of the healthcare facility",
    )
    address = Field(
        display="Facility Address",
        preview_value="123 Main St, Springfield",
        description="Address of the healthcare facility",
    )
    pincode = Field(
        display="Pincode",
        preview_value="123456",
        description="Pincode of the healthcare facility",
    )

    phone_number = Field(
        display="Contact Number",
        preview_value="+1-555-1234",
        description="Contact number of the healthcare facility",
    )
