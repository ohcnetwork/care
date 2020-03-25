from django.contrib import admin

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


class FacilityAdmin(admin.ModelAdmin):
    search_fields = ["name"]


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
admin.site.register(PatientRegistration)
admin.site.register(PatientTeleConsultation)
