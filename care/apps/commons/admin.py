from django.contrib import admin
from apps.commons import models as commons_models

from import_export.admin import ImportExportModelAdmin


class OwnershipTypeAdmin(ImportExportModelAdmin):
    search_fields = ("name",)


admin.site.register(commons_models.OwnershipType, OwnershipTypeAdmin)
