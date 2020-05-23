from django.contrib import admin
from django.contrib.admin import SimpleListFilter

from djangoql.admin import DjangoQLSearchMixin
from import_export.admin import ImportExportModelAdmin

from apps.facility import models as facility_models


class BuildingAdmin(admin.ModelAdmin):
    autocomplete_fields = ["facility"]
    search_fields = ["name"]


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
    list_filter = [StateFilter, DistrictFilter]
    djangoql_completion_enabled_by_default = True


class FacilityStaffAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    autocomplete_fields = ["facility", "staff"]
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


class AmbulanceDriverInline(DjangoQLSearchMixin, admin.TabularInline):
    model = facility_models.AmbulanceDriver
    djangoql_completion_enabled_by_default = True


class AmbulanceAdmin(admin.ModelAdmin):
    search_fields = ["vehicle_number"]
    inlines = [
        AmbulanceDriverInline,
    ]
    djangoql_completion_enabled_by_default = True


class AmbulanceDriverAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    autocomplete_fields = ["ambulance"]
    djangoql_completion_enabled_by_default = True


class PatientAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    list_display = ("id", "name", "age", "gender")
    djangoql_completion_enabled_by_default = True


class PatientSampleAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    djangoql_completion_enabled_by_default = True


class TestingLabAdmin(DjangoQLSearchMixin, ImportExportModelAdmin):
    model = facility_models.TestingLab
    djangoql_completion_enabled_by_default = True


admin.site.register(facility_models.Ambulance, AmbulanceAdmin)
admin.site.register(facility_models.AmbulanceDriver, AmbulanceDriverAdmin)
admin.site.register(facility_models.Facility, FacilityAdmin)
admin.site.register(facility_models.FacilityLocalGovtBody)
admin.site.register(facility_models.HospitalDoctors)
admin.site.register(facility_models.FacilityCapacity, FacilityCapacityAdmin)
admin.site.register(facility_models.FacilityStaff, FacilityStaffAdmin)
admin.site.register(facility_models.Building, BuildingAdmin)
admin.site.register(facility_models.Room, RoomAdmin)
admin.site.register(facility_models.StaffRoomAllocation, StaffRoomAllocationAdmin)
admin.site.register(facility_models.InventoryItem, InventoryItemAdmin)
admin.site.register(facility_models.Inventory, InventoryAdmin)
admin.site.register(facility_models.InventoryLog)
admin.site.register(facility_models.FacilityVolunteer, FacilityVolunteerAdmin)
admin.site.register(facility_models.FacilityUser)
admin.site.register(facility_models.TestingLab, TestingLabAdmin)
admin.site.register(facility_models.FacilityType)
