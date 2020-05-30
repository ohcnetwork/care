from django.contrib import admin
from django.contrib.admin import SimpleListFilter

from djangoql.admin import DjangoQLSearchMixin
from import_export.admin import ImportExportModelAdmin

from apps.facility import models as facility_models


class DistrictFilter(SimpleListFilter):
    """DistrictFilter """

    title = "District"
    parameter_name = "district"

    def lookups(self, request, model_admin):
        district = facility_models.Facility.objects.values_list(
            "district__name", flat=True
        )
        return list(map(lambda x: (x, x), set(district)))

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        return queryset.filter(district__name=self.value())


class StateFilter(SimpleListFilter):
    """State filter"""

    title = "State"
    parameter_name = "state"

    def lookups(self, request, model_admin):
        state = facility_models.Facility.objects.values_list("state__name", flat=True)
        return list(map(lambda x: (x, x), set(state)))

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        return queryset.filter(state__name=self.value())


class FacilityAdmin(DjangoQLSearchMixin, ImportExportModelAdmin):
    search_fields = ["name"]
    djangoql_completion_enabled_by_default = True


class FacilityTypeAdmin(ImportExportModelAdmin):
    search_fields = ["name"]


class FacilityStaffAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    autocomplete_fields = ["facility"]
    djangoql_completion_enabled_by_default = True


class InventoryAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    autocomplete_fields = ["facility", "item"]
    djangoql_completion_enabled_by_default = True


class InventoryItemAdmin(DjangoQLSearchMixin, ImportExportModelAdmin):
    search_fields = ("name", )
    djangoql_completion_enabled_by_default = True


class PatientAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    list_display = ("id", "name", "age", "gender")
    djangoql_completion_enabled_by_default = True


class PatientSampleAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    djangoql_completion_enabled_by_default = True


class TestingLabAdmin(DjangoQLSearchMixin, ImportExportModelAdmin):
    model = facility_models.TestingLab
    djangoql_completion_enabled_by_default = True


admin.site.register(facility_models.Facility, FacilityAdmin)
admin.site.register(facility_models.FacilityInfrastructure)
admin.site.register(facility_models.FacilityStaff, FacilityStaffAdmin)
admin.site.register(facility_models.InventoryItem, InventoryItemAdmin)
admin.site.register(facility_models.Inventory, InventoryAdmin)
admin.site.register(facility_models.FacilityUser)
admin.site.register(facility_models.TestingLab, TestingLabAdmin)
admin.site.register(facility_models.FacilityType, FacilityTypeAdmin)
admin.site.register(facility_models.RoomType)
admin.site.register(facility_models.BedType)
