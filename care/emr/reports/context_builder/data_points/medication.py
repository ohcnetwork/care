from decimal import Decimal

from django_filters import rest_framework as filters

from care.emr.models.medication_request import (
    MedicationRequest,
    MedicationRequestPrescription,
)
from care.emr.reports.context_builder.data_points.base import (
    Field,
    QuerysetContextBuilder,
)
from care.emr.reports.context_builder.data_points.user import (
    SingleUserRelatedContextBuilder,
)
from care.utils.filters.multiselect import MultiSelectFilter

STATUS_DISPLAY = {
    "active": "Active",
    "on_hold": "On Hold",
    "cancelled": "Cancelled",
    "completed": "Completed",
    "entered_in_error": "Entered in Error",
    "stopped": "Stopped",
    "draft": "Draft",
    "unknown": "Unknown",
}

INTENT_DISPLAY = {
    "proposal": "Proposal",
    "plan": "Plan",
    "order": "Order",
    "original_order": "Original Order",
    "reflex_order": "Reflex Order",
    "filler_order": "Filler Order",
    "instance_order": "Instance Order",
    "option": "Option",
}

PRIORITY_DISPLAY = {
    "routine": "Routine",
    "urgent": "Urgent",
    "asap": "ASAP",
    "stat": "STAT",
}


class MedicationRequestReportFilter(filters.FilterSet):
    intent = filters.CharFilter(lookup_expr="iexact")
    priority = filters.CharFilter(lookup_expr="iexact")
    status = MultiSelectFilter(field_name="status")
    exclude_status = MultiSelectFilter(field_name="status", exclude=True)


class MedicationPrescriptionReportFilter(filters.FilterSet):
    status = filters.CharFilter(lookup_expr="iexact")


class DosageInstructionContextBuilder(QuerysetContextBuilder):
    def get_context(self):
        return self.parent_context.dosage_instruction

    dosage = Field(
        display="Dosage",
        mapping=lambda d: (
            f"{int(d.get('dose_and_rate', {}).get('dose_quantity', {}).get('value', 0)) if Decimal(d.get('dose_and_rate', {}).get('dose_quantity', {}).get('value', 0)) % 1 == 0 else d.get('dose_and_rate', {}).get('dose_quantity', {}).get('value', '')} "
            f"{d.get('dose_and_rate', {}).get('dose_quantity', {}).get('unit', {}).get('display', '')}"
            if d.get("dose_and_rate")
            and d.get("dose_and_rate", {}).get("dose_quantity")
            else ""
        ).strip(),
        preview_value="2 tablet",
        description="Dose quantity for the medication",
    )

    frequency = Field(
        display="Frequency",
        mapping=lambda d: (
            d.get("timing", {}).get("code", {}).get("display", "")
            if d.get("timing")
            and d.get("timing").get("code")
            and d.get("timing", {}).get("code", {}).get("display")
            else "As Per Needed"
        ),
        preview_value="3 times every 1 day",
        description="Frequency of the medication dosage",
    )

    duration = Field(
        display="Duration",
        mapping=lambda d: (
            f"{int(d.get('timing', {}).get('repeat', {}).get('bounds_duration', {}).get('value', 0)) if Decimal(d.get('timing', {}).get('repeat', {}).get('bounds_duration', {}).get('value', 0)) % 1 == 0 else d.get('timing', {}).get('repeat', {}).get('bounds_duration', {}).get('value', '')} "
            f"{d.get('timing', {}).get('repeat', {}).get('bounds_duration', {}).get('unit', '')}"
            if d.get("timing", {}).get("repeat", {}).get("bounds_duration")
            else ""
        ).strip(),
        preview_value="2 d",
        description="Duration for which the medication is to be taken",
    )

    site = Field(
        display="Site",
        mapping=lambda d: d.get("site", {}).get("display", "") if d.get("site") else "",
        preview_value="Structure of product of conception of ectopic pregnancy",
        description="Site of administration for the medication",
    )

    method = Field(
        display="Method",
        mapping=lambda d: d.get("method", {}).get("display", "")
        if d.get("method")
        else "",
        preview_value="Injection",
        description="Method of administration for the medication",
    )
    route = Field(
        display="Route",
        mapping=lambda d: d.get("route", {}).get("display", "")
        if d.get("route")
        else "",
        preview_value="Peritumoural route",
        description="Route of administration for the medication",
    )


class MedicationRequestContextBuilder(QuerysetContextBuilder):
    filterset_class = MedicationRequestReportFilter
    __filterset_backends__ = [filters.DjangoFilterBackend]

    name = Field(
        display="Medication",
        preview_value="Morphine sulfate 60 mg oral tablet",
        mapping=lambda m: (
            m.medication.get("display", "")
            if m.medication
            else (m.requested_product.name if m.requested_product else "")
        ),
        description="Name of the medication",
    )
    status = Field(
        display="Status",
        preview_value="Active",
        mapping=lambda m: STATUS_DISPLAY.get(m.status, m.status.title())
        if m.status
        else "",
        description="Status of the medication",
    )
    intent = Field(
        display="Intent",
        preview_value="Order",
        mapping=lambda m: INTENT_DISPLAY.get(m.intent, m.intent.title())
        if m.intent
        else "",
        description="Intent of the medication",
    )
    priority = Field(
        display="Priority",
        preview_value="Routine",
        mapping=lambda m: PRIORITY_DISPLAY.get(m.priority, m.priority.title())
        if m.priority
        else "",
        description="Priority of the medication",
    )
    authored_on = Field(
        display="Authored On",
        preview_value="2025-11-30T18:30:00Z",
        description="Date when the medication was authored",
    )
    dosage_instructions = Field(
        display="Dosage Instructions",
        preview_value="",
        description="Dosage instructions for the medication",
        target_context=DosageInstructionContextBuilder,
    )
    note = Field(
        display="Note",
        preview_value="",
        description="Additional notes about the medication",
    )

    def get_context(self):
        return MedicationRequest.objects.filter(prescription=self.parent_context)


class MedicationPrescriptionContextBuilder(QuerysetContextBuilder):
    filterset_class = MedicationPrescriptionReportFilter
    __filterset_backends__ = [filters.DjangoFilterBackend]

    medications = Field(
        display="Medication",
        preview_value="",
        target_context=MedicationRequestContextBuilder,
        description="Details of the medication prescription",
    )
    status = Field(
        display="Status",
        preview_value="active",
        description="Status of the medication prescription",
    )
    prescribed_by = Field(
        display="Prescribed By",
        preview_value="",
        target_context=SingleUserRelatedContextBuilder,
        description="Details of the prescriber",
    )

    def get_context(self):
        return MedicationRequestPrescription.objects.filter(
            encounter=self.parent_context
        )
