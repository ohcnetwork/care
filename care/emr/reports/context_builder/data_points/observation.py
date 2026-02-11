from care.emr.models.observation import Observation
from care.emr.reports.context_builder.data_points.base import (
    Field,
    QuerysetContextBuilder,
    SingleObjectContextBuilder,
)


class ObservationReferenceRangeContextBuilder(QuerysetContextBuilder):
    def get_context(self):
        return getattr(self.parent_context, self.parent_attribute)

    max = Field(
        display="Reference Range Max",
        preview_value="14",
        mapping=lambda o: o.get("max") if o else None,
        description="The maximum value of the reference range",
    )
    min = Field(
        display="Reference Range Min",
        preview_value="4",
        mapping=lambda o: o.get("min") if o else None,
        description="The minimum value of the reference range",
    )
    interpretation = Field(
        display="Reference Range Interpretation",
        preview_value="Normal",
        mapping=lambda o: o.get("interpretation").get("display")
        if o and o.get("interpretation") and o.get("interpretation").get("display")
        else "",
        description="The clinical interpretation of the reference range",
    )


class ObservationComponentReferenceRangeContextBuilder(
    ObservationReferenceRangeContextBuilder
):
    def get_context(self):
        return self.parent_context.get("reference_range")


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


class ObservationComponentValueContextBuilder(ObservationValueContextBuilder):
    def get_context(self):
        return self.parent_context.get("value")


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
    value = Field(
        display="Observation Component Result",
        preview_value="",
        target_context=ObservationComponentValueContextBuilder,
        description="The result value of the observation component",
    )

    reference_range = Field(
        display="Observation Component Reference Ranges",
        preview_value="",
        target_context=ObservationComponentReferenceRangeContextBuilder,
        description="Reference ranges for the observation component",
    )

    interpretation = Field(
        display="Observation Component Interpretation",
        preview_value="High",
        mapping=lambda o: o.get("interpretation").get("display")
        if o and o.get("interpretation") and o.get("interpretation").get("display")
        else "",
        description="The clinical interpretation of the observation component",
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

    interpretation = Field(
        display="Interpretation",
        preview_value="Normal",
        mapping=lambda o: o.interpretation.get("display") if o.interpretation else "",
        description="The clinical interpretation of the observation",
    )

    reference_range = Field(
        display="Reference Range",
        preview_value="",
        target_context=ObservationReferenceRangeContextBuilder,
        description="Reference ranges for the observation",
    )
