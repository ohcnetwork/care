from django_filters import rest_framework as filters

from care.emr.models.condition import Condition
from care.emr.reports.context_builder.data_points.base import (
    Field,
    QuerysetContextBuilder,
)
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
    code = Field(
        display="Code",
        preview_value={
            {
                "code": {
                    "display": "Fever",
                    "system": "http://snomed.info/sct",
                    "code": "386661006",
                }
            }
        },
        description="Code of the symptom",
    )

    onset = Field(
        display="Onset",
        preview_value={"onset_datetime": "2025-11-24T00:00:00+05:30"},
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
