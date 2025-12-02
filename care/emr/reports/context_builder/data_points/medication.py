from django_filters import rest_framework as filters

from care.emr.reports.context_builder.data_points.base import (
    Field,
    QuerysetContextBuilder,
)


class MedicationReportFilter(filters.FilterSet):
    status = filters.CharFilter(lookup_expr="iexact")
    intent = filters.CharFilter(lookup_expr="iexact")
    priority = filters.CharFilter(lookup_expr="iexact")


class DosageInstructionContextBuilder(QuerysetContextBuilder):
    def get_context(self) -> dict:
        return self.parent_context.dosage_instructions

    dosage = Field(
        display="Dosage",
        mapping=lambda d: (
            f"{d.dosa_and_rate.dose_quantity.value} {d.dosa_and_rate.dose_quantity.unit.display}"
            if d.dosa_and_rate
            and d.dosa_and_rate.dose_quantity
            and d.dosa_and_rate.dose_quantity.unit
            else ""
        ),
        preview_value="2 tablet",
        description="Dose quantity for the medication",
    )

    frequency = Field(
        display="Frequency",
        mapping=lambda d: f"{d.timing.code.display}"
        if d.timing and d.timing.code
        else "",
        preview_value="3 times every 1 day",
        description="Frequency of the medication dosage",
    )

    duration = Field(
        display="Duration",
        mapping=lambda d: (
            f"{d.timing.repeat.duration.unit} {d.timing.repeat.duration.value}"
            if d.timing and d.timing.repeat and d.timing.repeat.duration
            else ""
        ),
        preview_value="2 d",
        description="Duration for which the medication is to be taken",
    )

    site = Field(
        display="Site",
        mapping=lambda d: d.site.display if d.site else "",
        preview_value="Structure of product of conception of ectopic pregnancy",
        description="Site of administration for the medication",
    )

    method = Field(
        display="Method",
        mapping=lambda d: d.method.display if d.method else "",
        preview_value="Injection",
        description="Method of administration for the medication",
    )
    route = Field(
        display="Route",
        mapping=lambda d: d.route.display if d.route else "",
        preview_value="Peritumoural route",
        description="Route of administration for the medication",
    )
