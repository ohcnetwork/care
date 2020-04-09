from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from djangoql.admin import DjangoQLSearchMixin

from care.facility.models.ambulance import Ambulance, AmbulanceDriver
from care.facility.models.patient_sample import PatientSample
from care.facility.models.patient_tele_consultation import PatientTeleConsultation

from .models import (
    Building,
    Disease,
    Facility,
    FacilityCapacity,
    FacilityStaff,
    FacilityVolunteer,
    Inventory,
    InventoryItem,
    InventoryLog,
    PatientRegistration,
    Room,
    StaffRoomAllocation,
)


class BuildingAdmin(admin.ModelAdmin):
    autocomplete_fields = ["facility"]
    search_fields = ["name"]


class DistrictFilter(SimpleListFilter):
    """DistrictFilter """

    title = "District"
    parameter_name = "district"

    def lookups(self, request, model_admin):
        district = Facility.objects.values_list("district__name", flat=True)
        return list(map(lambda x: (x, x), set(district)))

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        return queryset.filter(district__name=self.value())


# class LocalBodyFilter(SimpleListFilter):
#     """Local body filter"""

#     title = "Local body"
#     parameter_name = "local_body"

#     def lookups(self, request, model_admin):
#         local_body = Facility.objects.values_list("local_body__name", flat=True)
#         return list(map(lambda x: (x, x), set(local_body)))

#     def queryset(self, request, queryset):
#         if self.value() is None:
#             return queryset
#         return queryset.filter(local_body__name=self.value())


class StateFilter(SimpleListFilter):
    """State filter"""

    title = "State"
    parameter_name = "state"

    def lookups(self, request, model_admin):
        state = Facility.objects.values_list("state__name", flat=True)
        return list(map(lambda x: (x, x), set(state)))

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        return queryset.filter(state__name=self.value())


class FacilityAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
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
    model = AmbulanceDriver
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


admin.site.register(Facility, FacilityAdmin)
admin.site.register(FacilityStaff, FacilityStaffAdmin)
admin.site.register(FacilityCapacity, FacilityCapacityAdmin)
admin.site.register(FacilityVolunteer, FacilityVolunteerAdmin)
admin.site.register(Building, BuildingAdmin)
admin.site.register(Room, RoomAdmin)
admin.site.register(StaffRoomAllocation, StaffRoomAllocationAdmin)
admin.site.register(InventoryItem, InventoryItemAdmin)
admin.site.register(Inventory, InventoryAdmin)
admin.site.register(InventoryLog)
admin.site.register(Ambulance, AmbulanceAdmin)
admin.site.register(AmbulanceDriver, AmbulanceDriverAdmin)
admin.site.register(PatientRegistration, PatientAdmin)
admin.site.register(PatientTeleConsultation)
admin.site.register(PatientSample, PatientSampleAdmin)
admin.site.register(Disease)
