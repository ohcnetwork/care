from django.contrib import admin
from import_export import fields, resources
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget

from care.emr.models import Encounter, FacilityLocation, Patient, TokenBooking
from care.facility.models import Facility


class EncounterResource(resources.ModelResource):
    patient = fields.Field(
        column_name="patient",
        attribute="patient",
        widget=ForeignKeyWidget(Patient, "external_id"),
    )

    facility = fields.Field(
        column_name="facility",
        attribute="facility",
        widget=ForeignKeyWidget(Facility, "external_id"),
    )

    appointment = fields.Field(
        column_name="appointment",
        attribute="appointment",
        widget=ForeignKeyWidget(TokenBooking, "external_id"),
    )

    current_location = fields.Field(
        column_name="current_location",
        attribute="current_location",
        widget=ForeignKeyWidget(FacilityLocation, "external_id"),
    )

    class Meta:
        model = Encounter
        import_id_fields = ("external_id",)
        exclude = ("facility_organization_cache",)
        fields = (
            "external_id",
            "status",
            "status_history",
            "encounter_class",
            "encounter_class_history",
            "patient",
            "period",
            "facility",
            "appointment",
            "hospitalization",
            "priority",
            "external_identifier",
            "care_team",
            "current_location",
            "discharge_summary_advice",
        )
        export_order = fields


@admin.register(Encounter)
class EncounterAdmin(ImportExportModelAdmin):
    resource_class = EncounterResource
    list_display = ("external_id", "patient", "facility", "status", "priority")
    search_fields = ("external_id", "external_identifier", "status")
