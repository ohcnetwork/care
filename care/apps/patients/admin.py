from django.contrib import admin
from djangoql.admin import DjangoQLSearchMixin
from apps.patients import models

class PatientAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    list_display = ("id", "name", "age", "gender")
    djangoql_completion_enabled_by_default = True


class PatientSampleAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    djangoql_completion_enabled_by_default = True

admin.site.register(models.Patient, PatientAdmin)
admin.site.register(models.PatientFacility)
admin.site.register(models.PatientSampleTest, PatientSampleAdmin)
admin.site.register(models.PatientConsultation)
admin.site.register(models.DailyRound)
admin.site.register(models.PatientSampleFlow)
admin.site.register(models.PatientSearch)
admin.site.register(models.PatientMetaInfo)
admin.site.register(models.PatientContactDetails)
admin.site.register(models.Disease)
admin.site.register(models.FacilityPatientStatsHistory)
