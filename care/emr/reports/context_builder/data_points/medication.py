from django_filters import rest_framework as filters

from care.emr.models.medication_request import MedicationRequest
from care.emr.reports.context_builder.data_points.base import (
    Field,
    QuerysetContextBuilder,
)
from care.emr.reports.context_builder.utils import format_datetime


class MedicationReportFilter(filters.FilterSet):
    status = filters.CharFilter(lookup_expr="iexact")
    intent = filters.CharFilter(lookup_expr="iexact")
    priority = filters.CharFilter(lookup_expr="iexact")


class DosageInstructionContextBuilder(QuerysetContextBuilder):
    def get_context(self) -> dict:
        return self.parent_context.dosage_instructions

    dosage = Field(
        display="Dosage",
        mapping=lambda d: (
            f"{d.dosa_and_rate.dose_quantity.value} {d.dosa_and_rate.dose_quantity.unit.display}"
            if d.dosa_and_rate
            and d.dosa_and_rate.dose_quantity
            and d.dosa_and_rate.dose_quantity.unit
            else ""
        ),
        preview_value="2 tablet",
        description="Dose quantity for the medication",
    )

    frequency = Field(
        display="Frequency",
        mapping=lambda d: f"{d.timing.code.display}"
        if d.timing and d.timing.code
        else "",
        preview_value="3 times every 1 day",
        description="Frequency of the medication dosage",
    )

    duration = Field(
        display="Duration",
        mapping=lambda d: (
            f"{d.timing.repeat.duration.unit} {d.timing.repeat.duration.value}"
            if d.timing and d.timing.repeat and d.timing.repeat.duration
            else ""
        ),
        preview_value="2 d",
        description="Duration for which the medication is to be taken",
    )

    site = Field(
        display="Site",
        mapping=lambda d: d.site.display if d.site else "",
        preview_value="Structure of product of conception of ectopic pregnancy",
        description="Site of administration for the medication",
    )

    method = Field(
        display="Method",
        mapping=lambda d: d.method.display if d.method else "",
        preview_value="Injection",
        description="Method of administration for the medication",
    )
    route = Field(
        display="Route",
        mapping=lambda d: d.route.display if d.route else "",
        preview_value="Peritumoural route",
        description="Route of administration for the medication",
    )


class MedicationRequestContextBuilder(QuerysetContextBuilder):
    filterset_class = MedicationReportFilter
    __filterset_backends__ = [filters.DjangoFilterBackend]

    medication = Field(
        display="Medication",
        preview_value="Morphine sulfate 60 mg oral tablet",
        mapping=lambda m: m.medication.display if m.medication else "",
        description="Details of the medication",
    )
    status = Field(
        display="Status",
        preview_value="active",
        description="Status of the medication",
    )
    intent = Field(
        display="Intent",
        preview_value="order",
        description="Intent of the medication",
    )
    priority = Field(
        display="Priority",
        preview_value="routine",
        description="Priority of the medication",
    )
    authored_on = Field(
        display="Authored On",
        mapping=lambda m: format_datetime(m.authored_on) if m.authored_on else "",
        preview_value="10/01/2024 10:30 AM",
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

    def get_context(self) -> dict:
        return MedicationRequest.objects.filter(encounter=self.parent_context)
