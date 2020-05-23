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
admin.site.register(models.Disease)
