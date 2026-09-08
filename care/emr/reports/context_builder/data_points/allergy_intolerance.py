from django_filters import rest_framework as filters

from care.emr.models.allergy_intolerance import AllergyIntolerance
from care.emr.reports.context_builder.data_points.base import (
    Field,
    QuerysetContextBuilder,
)
from care.utils.filters.multiselect import MultiSelectFilter

CLINICAL_STATUS_DISPLAY = {
    "active": "Active",
    "inactive": "Inactive",
    "resolved": "Resolved",
}

CATEGORY_DISPLAY = {
    "food": "Food",
    "medication": "Medication",
    "environment": "Environment",
    "biologic": "Biologic",
}

VERIFICATION_STATUS_DISPLAY = {
    "unconfirmed": "Unconfirmed",
    "confirmed": "Confirmed",
    "refuted": "Refuted",
    "entered_in_error": "Entered in Error",
}

CRITICALITY_DISPLAY = {
    "low": "Low",
    "high": "High",
    "unable_to_assess": "Unable to Assess",
}

ALLERGY_INTOLERANCE_TYPE_DISPLAY = {
    "allergy": "Allergy",
    "intolerance": "Intolerance",
}


class AllergyIntoleranceReportFilter(filters.FilterSet):
    clinical_status = MultiSelectFilter(field_name="clinical_status")
    exclude_clinical_status = MultiSelectFilter(
        field_name="clinical_status", exclude=True
    )
    verification_status = MultiSelectFilter(field_name="verification_status")
    exclude_verification_status = MultiSelectFilter(
        field_name="verification_status", exclude=True
    )


class AllergyIntoleranceContextBuilder(QuerysetContextBuilder):
    filterset_class = AllergyIntoleranceReportFilter
    __filterset_backends__ = [filters.DjangoFilterBackend]

    clinical_status = Field(
        display="Clinical Status",
        preview_value="Active",
        mapping=lambda a: (
            CLINICAL_STATUS_DISPLAY.get(a.clinical_status, a.clinical_status.title())
            if a.clinical_status
            else ""
        ),
        description="Clinical status of the allergy or intolerance",
    )
    category = Field(
        display="Category",
        preview_value="Food",
        mapping=lambda a: (
            CATEGORY_DISPLAY.get(a.category, a.category.title()) if a.category else ""
        ),
        description="Category of the allergy or intolerance",
    )
    verification_status = Field(
        display="Verification Status",
        preview_value="Confirmed",
        mapping=lambda a: (
            VERIFICATION_STATUS_DISPLAY.get(
                a.verification_status, a.verification_status.title()
            )
            if a.verification_status
            else ""
        ),
        description="Verification status of the allergy or intolerance",
    )
    criticality = Field(
        display="Criticality",
        preview_value="High",
        mapping=lambda a: (
            CRITICALITY_DISPLAY.get(a.criticality, a.criticality.title())
            if a.criticality
            else ""
        ),
        description="Criticality of the allergy or intolerance",
    )
    name = Field(
        display="Name",
        mapping=lambda a: a.code.get("display") if a.code else "",
        preview_value="Fezolinetant",
        description="Name representing the allergy or intolerance",
    )
    note = Field(
        display="Note",
        preview_value="Patient reports severe reaction to peanuts.",
        description="Additional notes about the allergy or intolerance",
    )
    last_occurrence = Field(
        display="Occurrence",
        preview_value="2025-12-03 12:09:13.880000+00:00",
        description="The last occurrence date and time of the allergy or intolerance",
    )
    allergy_intolerance_type = Field(
        display="Allergy Intolerance Type",
        preview_value="Allergy",
        mapping=lambda a: (
            ALLERGY_INTOLERANCE_TYPE_DISPLAY.get(
                a.allergy_intolerance_type, a.allergy_intolerance_type.title()
            )
            if a.allergy_intolerance_type
            else ""
        ),
    )

    def get_context(self):
        return AllergyIntolerance.objects.filter(encounter=self.parent_context)
