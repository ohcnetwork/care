from django_filters import rest_framework as filters

from care.emr.models.allergy_intolerance import AllergyIntolerance
from care.emr.reports.context_builder.data_points.base import (
    Field,
    QuerysetContextBuilder,
)


class AllergyIntoleranceReportFilter(filters.FilterSet):
    clinical_status = filters.CharFilter(lookup_expr="iexact")
    verification_status = filters.CharFilter(lookup_expr="iexact")


class AllergyIntoleranceContextBuilder(QuerysetContextBuilder):
    filterset_class = AllergyIntoleranceReportFilter
    __filterset_backends__ = [filters.DjangoFilterBackend]

    clinical_status = Field(
        display="Clinical Status",
        preview_value="Active",
        description="Clinical status of the allergy or intolerance",
    )
    verification_status = Field(
        display="Verification Status",
        preview_value="Confirmed",
        description="Verification status of the allergy or intolerance",
    )
    criticality = Field(
        display="Criticality",
        preview_value="High",
        description="Criticality of the allergy or intolerance",
    )
    code = Field(
        display="Code",
        preview_value={
            "code": {
                "code": "42544811000001108",
                "system": "http://snomed.info/sct",
                "display": "Fezolinetant",
            }
        },
        description="Code representing the allergy or intolerance",
    )
    note = Field(
        display="Note",
        preview_value="Patient reports severe reaction to peanuts.",
        description="Additional notes about the allergy or intolerance",
    )
    last_occurrence = Field(
        display="Occurrence",
        preview_value="2025-12-01",
        description="The last occurrence date and time of the allergy or intolerance",
    )
    onset = Field(
        display="Onset",
        preview_value={"onset_datetime": "2025-11-24T00:00:00+05:30"},
        description="The onset date of the allergy or intolerance",
    )

    def get_context(self) -> dict:
        return AllergyIntolerance.objects.filter(encounter=self.parent_context)
