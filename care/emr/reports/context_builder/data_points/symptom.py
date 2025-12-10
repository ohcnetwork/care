from django_filters import rest_framework as filters

from care.emr.models.condition import Condition
from care.emr.reports.context_builder.data_points.base import (
    Field,
    QuerysetContextBuilder,
)
from care.emr.reports.context_builder.data_points.user import SingleUserIdContextBuilder
from care.emr.resources.condition.spec import CategoryChoices
from care.utils.filters.multiselect import MultiSelectFilter

CLINICAL_STATUS_DISPLAY = {
    "active": "Active",
    "recurrence": "Recurrence",
    "relapse": "Relapse",
    "inactive": "Inactive",
    "remission": "Remission",
    "resolved": "Resolved",
    "unknown": "Unknown",
}

VERIFICATION_STATUS_DISPLAY = {
    "unconfirmed": "Unconfirmed",
    "provisional": "Provisional",
    "differential": "Differential",
    "confirmed": "Confirmed",
    "refuted": "Refuted",
    "entered_in_error": "Entered in Error",
}


class SymptomsReportFilter(filters.FilterSet):
    clinical_status = MultiSelectFilter(field_name="clinical_status")
    exclude_clinical_status = MultiSelectFilter(
        field_name="clinical_status", exclude=True
    )
    verification_status = MultiSelectFilter(field_name="verification_status")
    exclude_verification_status = MultiSelectFilter(
        field_name="verification_status", exclude=True
    )


class SymptomsContextBuilder(QuerysetContextBuilder):
    filterset_class = SymptomsReportFilter
    __filterset_backends__ = [filters.DjangoFilterBackend]

    clinical_status = Field(
        display="Clinical Status",
        preview_value="Active",
        mapping=lambda c: CLINICAL_STATUS_DISPLAY.get(
            c.clinical_status, c.clinical_status.title()
        )
        if c.clinical_status
        else "",
        description="Clinical status of the condition",
    )
    verification_status = Field(
        display="Verification Status",
        preview_value="Confirmed",
        mapping=lambda c: VERIFICATION_STATUS_DISPLAY.get(
            c.verification_status, c.verification_status.title()
        )
        if c.verification_status
        else "",
        description="Verification status of the condition",
    )
    name = Field(
        display="Name",
        mapping=lambda c: c.code.get("display") if c.code else "",
        preview_value="Fever",
        description="Name of the symptom",
    )

    onset = Field(
        display="Onset",
        mapping=lambda c: c.onset.get("onset_datetime") if c.onset else "",
        preview_value="2025-11-30T18:30:00Z",
        description="The onset date of the symptom",
    )

    note = Field(
        display="Note",
        preview_value="",
        description="Additional notes about the symptom",
    )
    created_by = Field(
        display="Created By",
        target_context=SingleUserIdContextBuilder,
        preview_value="",
        description="User who created the symptom",
    )
    updated_by = Field(
        display="Updated By",
        target_context=SingleUserIdContextBuilder,
        preview_value="",
        description="User who updated the symptom",
    )

    def get_context(self):
        return Condition.objects.filter(
            encounter=self.parent_context,
            category=CategoryChoices.problem_list_item.value,
        )
