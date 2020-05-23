from django.contrib import admin
from django.contrib.admin import SimpleListFilter

from djangoql.admin import DjangoQLSearchMixin
from import_export.admin import ImportExportModelAdmin

from apps.facility import models as accounts_models


class DistrictFilter(SimpleListFilter):
    """DistrictFilter """

    title = "District"
    parameter_name = "district"

    def lookups(self, request, model_admin):
        district = accounts_models.Facility.objects.values_list(
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
        state = accounts_models.Facility.objects.values_list("state__name", flat=True)
        return list(map(lambda x: (x, x), set(state)))

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        return queryset.filter(state__name=self.value())


class FacilityAdmin(DjangoQLSearchMixin, ImportExportModelAdmin):
    search_fields = ["name"]
    list_filter = [StateFilter, DistrictFilter]
    djangoql_completion_enabled_by_default = True


class FacilityStaffAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    autocomplete_fields = ["facility"]
    djangoql_completion_enabled_by_default = True


class FacilityCapacityAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    autocomplete_fields = ["facility"]
    djangoql_completion_enabled_by_default = True


class FacilityVolunteerAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    autocomplete_fields = ["facility", "volunteer"]
    djangoql_completion_enabled_by_default = True


class InventoryAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    autocomplete_fields = ["facility", "item"]
    djangoql_completion_enabled_by_default = True


class InventoryItemAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    search_fields = ["name", "description"]
    djangoql_completion_enabled_by_default = True


class RoomAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    autocomplete_fields = ["building"]
    search_fields = ["building", "num"]
    djangoql_completion_enabled_by_default = True


class StaffRoomAllocationAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    autocomplete_fields = ["staff", "room"]
    djangoql_completion_enabled_by_default = True


class PatientAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    list_display = ("id", "name", "age", "gender")
    djangoql_completion_enabled_by_default = True


class PatientSampleAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    djangoql_completion_enabled_by_default = True


class TestingLabAdmin(DjangoQLSearchMixin, ImportExportModelAdmin):
    model = accounts_models.TestingLab
    djangoql_completion_enabled_by_default = True


admin.site.register(accounts_models.Facility, FacilityAdmin)
admin.site.register(accounts_models.FacilityStaff, FacilityStaffAdmin)
admin.site.register(accounts_models.InventoryItem, InventoryItemAdmin)
admin.site.register(accounts_models.Inventory, InventoryAdmin)
admin.site.register(accounts_models.FacilityUser)
admin.site.register(accounts_models.TestingLab, TestingLabAdmin)
