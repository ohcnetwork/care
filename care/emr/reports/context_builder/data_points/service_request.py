from django_filters import rest_framework as filters

from care.emr.models.service_request import ServiceRequest
from care.emr.reports.context_builder.data_points.base import (
    Field,
    QuerysetContextBuilder,
)
from care.emr.reports.context_builder.data_points.user import SingleUserIdContextBuilder
from care.emr.reports.context_builder.utils import format_datetime


class ServiceRequestReportFilterSet(filters.FilterSet):
    status = filters.CharFilter(field_name="status", lookup_expr="iexact")
    intent = filters.CharFilter(field_name="intent", lookup_expr="iexact")
    category = filters.CharFilter(field_name="category", lookup_expr="iexact")
    priority = filters.CharFilter(field_name="priority", lookup_expr="iexact")


class ServiceRequestDataPointBuilder(QuerysetContextBuilder):
    filterset_class = ServiceRequestReportFilterSet
    __filterset_backends__ = [filters.DjangoFilterBackend]

    title = Field(
        display="Title",
        preview_value="Complete Blood Count",
        description="Title of the service request",
    )
    status = Field(
        display="Status",
        preview_value="active",
        description="Current status of the service request",
    )
    intent = Field(
        display="Intent",
        preview_value="order",
        description="Intent of the service request",
    )
    category = Field(
        display="Category",
        preview_value="laboratory",
        description="Category of the service request",
    )

    occurance = Field(
        display="Occurrence",
        mapping=lambda sr: format_datetime(sr.occurance) if sr.occurance else "",
        preview_value="2023-01-01 10:00 AM",
        description="Date and time when the service is to occur",
    )

    requester = Field(
        display="Requester",
        target_context=SingleUserIdContextBuilder,
        preview_value="",
        description="User who requested the service",
    )

    def get_context(self) -> dict:
        return ServiceRequest.objects.filter(encounter=self.parent_context)
