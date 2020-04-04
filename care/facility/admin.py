from django.contrib import admin
from django.contrib.admin import SimpleListFilter

from care.facility.models.patient_sample import PatientSample

from .models import (
    Ambulance,
    AmbulanceDriver,
    Building,
    Facility,
    FacilityCapacity,
    FacilityStaff,
    FacilityVolunteer,
    Inventory,
    InventoryItem,
    InventoryLog,
    PatientRegistration,
    PatientTeleConsultation,
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


class FacilityAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    list_filter = [StateFilter, DistrictFilter]


class FacilityStaffAdmin(admin.ModelAdmin):
    autocomplete_fields = ["facility", "staff"]


class FacilityCapacityAdmin(admin.ModelAdmin):
    autocomplete_fields = ["facility"]


class FacilityVolunteerAdmin(admin.ModelAdmin):
    autocomplete_fields = ["facility", "volunteer"]


class InventoryAdmin(admin.ModelAdmin):
    autocomplete_fields = ["facility", "item"]


class InventoryItemAdmin(admin.ModelAdmin):
    search_fields = ["name", "description"]


class RoomAdmin(admin.ModelAdmin):
    autocomplete_fields = ["building"]
    search_fields = ["building", "num"]


class StaffRoomAllocationAdmin(admin.ModelAdmin):
    autocomplete_fields = ["staff", "room"]


class AmbulanceDriverInline(admin.TabularInline):
    model = AmbulanceDriver


class AmbulanceAdmin(admin.ModelAdmin):
    search_fields = ["vehicle_number"]
    inlines = [
        AmbulanceDriverInline,
    ]


class AmbulanceDriverAdmin(admin.ModelAdmin):
    autocomplete_fields = ["ambulance"]


class PatientAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "age", "gender")


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
admin.site.register(PatientSample)
