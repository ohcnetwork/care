from django.contrib import admin
from import_export import fields, resources
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget

from care.emr.models import Organization, Patient


class PatientResource(resources.ModelResource):
    geo_organization = fields.Field(
        column_name="geo_organization",
        attribute="geo_organization",
        widget=ForeignKeyWidget(Organization, field="external_id"),
    )

    class Meta:
        model = Patient
        import_id_fields = ("external_id",)
        exclude = ("organization_cache", "users_cache")
        fields = (
            "external_id",
            "name",
            "gender",
            "phone_number",
            "emergency_phone_number",
            "address",
            "permanent_address",
            "pincode",
            "date_of_birth",
            "year_of_birth",
            "deceased_datetime",
            "marital_status",
            "blood_group",
            "geo_organization",
        )


@admin.register(Patient)
class PatientAdmin(ImportExportModelAdmin):
    resource_class = PatientResource
