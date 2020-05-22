from django.contrib import admin
from djangoql.admin import DjangoQLSearchMixin

from .models import (
    PatientRegistration, PatientSample, PatientTeleConsultation
)

class PatientAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    list_display = ("id", "name", "age", "gender")
    djangoql_completion_enabled_by_default = True


class PatientSampleAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    djangoql_completion_enabled_by_default = True

admin.site.register(PatientRegistration, PatientAdmin)
admin.site.register(PatientTeleConsultation)
admin.site.register(PatientSample, PatientSampleAdmin)
