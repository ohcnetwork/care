from django_filters import rest_framework as filters

from care.emr.models.condition import Condition
from care.emr.reports.context_builder.data_points.base import (
    Field,
    QuerysetContextBuilder,
)
from care.emr.reports.context_builder.data_points.user import (
    SingleUserRelatedContextBuilder,
)


class SymptomsReportFilter(filters.FilterSet):
    clinical_status = filters.CharFilter(lookup_expr="iexact")
    verification_status = filters.CharFilter(lookup_expr="iexact")


class SymptomsContextBuilder(QuerysetContextBuilder):
    filterset_class = SymptomsReportFilter
    __filterset_backends__ = [filters.DjangoFilterBackend]

    clinical_status = Field(
        key="clinical_status",
        display="Clinical Status",
        preview_value="Active",
        description="Clinical status of the condition",
    )
    verification_status = Field(
        key="verification_status",
        display="Verification Status",
        preview_value="Confirmed",
        description="Verification status of the condition",
    )
    created_by = Field(
        key="created_by",
        display="Created By",
        target_context=SingleUserRelatedContextBuilder,
        preview_value="",
        description="User who created the condition",
    )
    updated_by = Field(
        key="updated_by",
        display="Updated By",
        target_context=SingleUserRelatedContextBuilder,
        preview_value="",
        description="User who updated the condition",
    )

    def get_context(self) -> dict:
        return Condition.objects.filter(encounter=self.parent_context)
