from django_filters import rest_framework as filters

from care.emr.models.condition import Condition
from care.emr.reports.context_builder.data_points.base import (
    Field,
    QuerysetContextBuilder,
)
from care.emr.reports.context_builder.utils import format_datetime
from care.emr.resources.condition.spec import CategoryChoices


class SymptomsReportFilter(filters.FilterSet):
    clinical_status = filters.CharFilter(lookup_expr="iexact")
    verification_status = filters.CharFilter(lookup_expr="iexact")


class SymptomsContextBuilder(QuerysetContextBuilder):
    filterset_class = SymptomsReportFilter
    __filterset_backends__ = [filters.DjangoFilterBackend]

    clinical_status = Field(
        display="Clinical Status",
        preview_value="Active",
        description="Clinical status of the condition",
    )
    verification_status = Field(
        display="Verification Status",
        preview_value="Confirmed",
        description="Verification status of the condition",
    )
    name = Field(
        display="Name",
        mapping=lambda c: c.code.display if c.code else "",
        preview_value="Fever",
        description="Name of the symptom",
    )

    onset = Field(
        display="Onset",
        mapping=lambda c: format_datetime(c.onset.onset_datetime)
        if c.onset and c.onset.onset_datetime
        else "",
        preview_value="10/01/2024 10:30 AM",
        description="The onset date of the symptom",
    )

    note = Field(
        display="Note",
        preview_value="",
        description="Additional notes about the symptom",
    )

    def get_context(self) -> dict:
        return Condition.objects.filter(
            encounter=self.parent_context,
            category=CategoryChoices.problem_list_item.value,
        )
