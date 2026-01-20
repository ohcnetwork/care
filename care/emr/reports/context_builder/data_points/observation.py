from care.emr.reports.context_builder.data_points.base import (
    Field,
    QuerysetContextBuilder,
    SingleObjectContextBuilder,
)
from care.emr.resources.observation.spec import Observation


class ObservationValueContextBuilder(SingleObjectContextBuilder):
    def get_context(self):
        return getattr(self.parent_context, self.parent_attribute)

    value = Field(
        display="Observation Value",
        preview_value="12",
        mapping=lambda o: o.get("value") if o and o.get("value") else None,
        description="The value of the observation recorded",
    )

    unit = Field(
        display="Observation Unit",
        preview_value="%",
        mapping=lambda o: o.get("unit").get("code")
        if o and o.get("unit") and o.get("unit").get("code")
        else None,
        description="The unit of measurement for the observation",
    )


class ObservationComponentContextBuilder(QuerysetContextBuilder):
    def get_context(self):
        return self.parent_context.component

    title = Field(
        display="Observation Component Title",
        preview_value="Hemoglobin A1c",
        mapping=lambda o: o.get("code").get("display")
        if o and o.get("code") and o.get("code").get("display")
        else "",
        description="The code representing the observation",
    )
    result = Field(
        display="Observation Component Result",
        preview_value="",
        target_context=ObservationValueContextBuilder,
        description="The result value of the observation component",
    )


class ObservationContextBuilder(QuerysetContextBuilder):
    def get_context(self):
        return Observation.objects.filter(diagnostic_report=self.parent_context)

    title = Field(
        display="Observation Title",
        preview_value="Blood Glucose Level",
        mapping=lambda o: o.main_code.get("display")
        if o.main_code and o.main_code.get("display")
        else "",
        description="The code representing the observation",
    )
    value = Field(
        display="Observation Value",
        preview_value="",
        target_context=ObservationValueContextBuilder,
        description="The value of the observation recorded",
    )
    component = Field(
        display="Observation Component",
        preview_value="",
        target_context=ObservationComponentContextBuilder,
        description="Components of the observation",
    )
    status = Field(
        display="Observation Status",
        preview_value="final",
        description="The status of the observation",
    )

    effective_datetime = Field(
        display="Effective DateTime",
        preview_value="2023-10-01T10:00:00Z",
        description="The date and time when the observation was made",
    )
