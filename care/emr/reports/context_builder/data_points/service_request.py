from django_filters import rest_framework as filters

from care.emr.models import TagConfig
from care.emr.models.service_request import ServiceRequest
from care.emr.reports.context_builder import TagFilter
from care.emr.reports.context_builder.data_points.base import (
    Field,
    QuerysetContextBuilder,
)
from care.emr.reports.context_builder.data_points.user import (
    SingleUserRelatedContextBuilder,
)
from care.utils.filters.multiselect import MultiSelectFilter

STATUS_CHOICE = {
    "draft": "Draft",
    "active": "Active",
    "on_hold": "On Hold",
    "entered_in_error": "Entered in Error",
    "ended": "Ended",
    "completed": "Completed",
    "revoked": "Revoked",
}

INTENT_CHOICE = {
    "proposal": "Proposal",
    "plan": "Plan",
    "directive": "Directive",
    "order": "Order",
}

CATEGORY_CHOICE = {
    "laboratory": "Laboratory",
    "imaging": "Imaging",
    "counselling": "Counselling",
    "surgical_procedure": "Surgical Procedure",
}

PRIORITY_CHOICE = {
    "routine": "Routine",
    "urgent": "Urgent",
    "asap": "ASAP",
    "stat": "Stat",
}


class ServiceRequestTagContextBuilder(QuerysetContextBuilder):
    filterset_class = TagFilter
    __filterset_backends__ = [filters.DjangoFilterBackend]

    display = Field(
        display="Tag Display",
        preview_value="Preparing",
        mapping=lambda t: t.display if t else None,
        description="Display of the service request tag",
    )

    def get_context(self):
        return TagConfig.objects.filter(id__in=self.parent_context.tags)


class ServiceRequestReportFilterSet(filters.FilterSet):
    status = MultiSelectFilter(field_name="status")
    intent = filters.CharFilter(field_name="intent", lookup_expr="iexact")
    category = filters.CharFilter(field_name="category", lookup_expr="iexact")
    priority = filters.CharFilter(field_name="priority", lookup_expr="iexact")


class ServiceRequestBaseContextBuilder(QuerysetContextBuilder):
    filterset_class = ServiceRequestReportFilterSet
    __filterset_backends__ = [filters.DjangoFilterBackend]

    title = Field(
        display="Title",
        preview_value="Complete Blood Count",
        description="Title of the service request",
    )
    status = Field(
        display="Status",
        preview_value="Active",
        mapping=lambda sr: (
            STATUS_CHOICE.get(sr.status, sr.status.title()) if sr.status else ""
        ),
        description="Current status of the service request",
    )
    intent = Field(
        display="Intent",
        preview_value="Order",
        mapping=lambda sr: (
            INTENT_CHOICE.get(sr.intent, sr.intent.title()) if sr.intent else ""
        ),
        description="Intent of the service request",
    )
    category = Field(
        display="Category",
        preview_value="Laboratory",
        mapping=lambda sr: (
            CATEGORY_CHOICE.get(sr.category, sr.category.title()) if sr.category else ""
        ),
        description="Category of the service request",
    )

    priority = Field(
        display="Priority",
        preview_value="Routine",
        mapping=lambda sr: (
            PRIORITY_CHOICE.get(sr.priority, sr.priority.title()) if sr.priority else ""
        ),
        description="Priority level of the service request",
    )

    requester = Field(
        display="Requester",
        target_context=SingleUserRelatedContextBuilder,
        preview_value="",
        description="User who requested the service",
    )
    occurance = Field(
        display="Occurence",
        preview_value="2023-01-01",
        description="Date and time when service should occur",
    )
    patient_instruction = Field(
        display="Patient Instruction",
        preview_value="Follow up on blood count",
        description="Patient or consumer-oriented instructions",
    )
    tags = Field(
        display="Service Request Tags",
        target_context=ServiceRequestTagContextBuilder,
        preview_value="",
        description="Tags associated with the service request",
    )
    note = Field(
        display="Note",
        preview_value="Sample note",
        description="Additional notes about the service request",
    )

    def get_context(self):
        return ServiceRequest.objects.filter(encounter=self.parent_context)
