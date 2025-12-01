from django_filters import rest_framework as filters

from care.emr.models.allergy_intolerance import AllergyIntolerance
from care.emr.reports.context_builder.data_points.base import (
    Field,
    QuerysetContextBuilder,
)
from care.emr.reports.context_builder.data_points.user import (
    SingleUserRelatedContextBuilder,
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
    created_by = Field(
        display="Created By",
        target_context=SingleUserRelatedContextBuilder,
        preview_value="",
        description="User who created the allergy or intolerance record",
    )
    updated_by = Field(
        display="Updated By",
        target_context=SingleUserRelatedContextBuilder,
        preview_value="",
        description="User who updated the allergy or intolerance record",
    )

    def get_context(self) -> dict:
        return AllergyIntolerance.objects.filter(encounter=self.parent_context)
