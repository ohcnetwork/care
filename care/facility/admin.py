from django.contrib import admin

from .models import (
    Facility,
    FacilityLocation,
    FacilityStaff,
    FacilityVolunteer,
    Building,
    Room,
    StaffRoomAllocation,
    InventoryItem,
    Inventory,
    InventoryLog,
)


class BuildingAdmin(admin.ModelAdmin):
    autocomplete_fields = ['facility']
    search_fields = ['name']


class FacilityAdmin(admin.ModelAdmin):
    search_fields = ['facility']


class FacilityStaffAdmin(admin.ModelAdmin):
    autocomplete_fields = ['facility', 'staff']


class FacilityVolunteerAdmin(admin.ModelAdmin):
    autocomplete_fields = ['facility', 'volunteer']


class InventoryAdmin(admin.ModelAdmin):
    autocomplete_fields = ['facility', 'item']


class InventoryItemAdmin(admin.ModelAdmin):
    search_fields = ['name', 'description']


class RoomAdmin(admin.ModelAdmin):
    autocomplete_fields = ['building']
    search_fields = ['building', 'num']


class StaffRoomAllocationAdmin(admin.ModelAdmin):
    autocomplete_fields = ['staff', 'room']


admin.site.register(Facility, FacilityAdmin)
admin.site.register(FacilityLocation)
admin.site.register(FacilityStaff, FacilityStaffAdmin)
admin.site.register(FacilityVolunteer, FacilityVolunteerAdmin)
admin.site.register(Building, BuildingAdmin)
admin.site.register(Room, RoomAdmin)
admin.site.register(StaffRoomAllocation, StaffRoomAllocationAdmin)
admin.site.register(InventoryItem, InventoryItemAdmin)
admin.site.register(Inventory, InventoryAdmin)
admin.site.register(InventoryLog)
