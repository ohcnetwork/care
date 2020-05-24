from django.contrib import admin
from djangoql.admin import DjangoQLSearchMixin
from apps.patients import models


class PatientSymptomInline(admin.TabularInline):
    model = models.PatientSymptom
    min_num = 0
    extra = 1

class PatientDiseaseInline(admin.TabularInline):
    model = models.PatientDisease
    min_num = 0
    extra = 1

class PatientAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    list_display = ("id", "name", "age", "gender")
    inlines = [PatientSymptomInline, PatientDiseaseInline]
    djangoql_completion_enabled_by_default = True


class PatientSampleAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    djangoql_completion_enabled_by_default = True


admin.site.register(models.Patient, PatientAdmin)
admin.site.register(models.PatientFacility)
admin.site.register(models.Disease)
admin.site.register(models.CovidSymptom)
admin.site.register(models.PatientTimeLine)
