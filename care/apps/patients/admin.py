from django.contrib import admin
from djangoql.admin import DjangoQLSearchMixin
from apps.patients import models
from import_export.admin import ImportExportModelAdmin


class PatientSymptomInline(admin.TabularInline):
    model = models.PatientSymptom
    min_num = 0
    extra = 1


class PatientDiseaseInline(admin.TabularInline):
    model = models.PatientDisease
    min_num = 0
    extra = 1


class PatientAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    list_display = ("id", "name", "gender")
    inlines = [
        PatientSymptomInline,
        PatientDiseaseInline,
    ]
    djangoql_completion_enabled_by_default = True


class PatientSampleAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    djangoql_completion_enabled_by_default = True


class DiseaseAdmin(DjangoQLSearchMixin, ImportExportModelAdmin):
    model = models.Disease
    djangoql_completion_enabled_by_default = True


class CovidSymptomAdmin(DjangoQLSearchMixin, ImportExportModelAdmin):
    model = models.CovidSymptom
    djangoql_completion_enabled_by_default = True


class PatientStatusAdmin(DjangoQLSearchMixin, ImportExportModelAdmin):
    model = models.PatientStatus
    djangoql_completion_enabled_by_default = True


class PatientCovidStatusStatusAdmin(DjangoQLSearchMixin, ImportExportModelAdmin):
    model = models.CovidStatus
    djangoql_completion_enabled_by_default = True


class PatientClinicalStatusStatusAdmin(DjangoQLSearchMixin, ImportExportModelAdmin):
    model = models.ClinicalStatus
    djangoql_completion_enabled_by_default = True


class PatientTransferAdmin(ImportExportModelAdmin):
    raw_id_fields = (
        "from_patient_facility",
        "to_facility",
    )
    list_display = (
        "__str__",
        "status",
    )
    list_filter = ("status",)
    search_fields = ("from_patient_facility__patient__name",)


class PatientFacilityAdmin(admin.ModelAdmin):
    raw_id_fields = (
        "patient",
        "facility",
    )
    list_display = (
        "patient",
        "facility",
        "patient_status"
    )
    list_filter = ("patient_status",)
    search_fields = ("patient__name",)


admin.site.register(models.Patient, PatientAdmin)
admin.site.register(models.PatientFacility, PatientFacilityAdmin)
admin.site.register(models.Disease, DiseaseAdmin)
admin.site.register(models.PatientGroup, ImportExportModelAdmin)
admin.site.register(models.CovidSymptom, CovidSymptomAdmin)
admin.site.register(models.PatientStatus, PatientStatusAdmin)
admin.site.register(models.CovidStatus, PatientCovidStatusStatusAdmin)
admin.site.register(models.ClinicalStatus, PatientClinicalStatusStatusAdmin)
admin.site.register(models.PatientTimeLine)
admin.site.register(models.PatientFamily)
admin.site.register(models.PortieCallingDetail)
admin.site.register(models.PatientSampleTest)
admin.site.register(models.PatientTransfer, PatientTransferAdmin)
