from django.contrib import admin

from facility.models import (
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

admin.site.register(Facility)
admin.site.register(FacilityLocation)
admin.site.register(FacilityStaff)
admin.site.register(FacilityVolunteer)
admin.site.register(Building)
admin.site.register(Room)
admin.site.register(StaffRoomAllocation)
admin.site.register(InventoryItem)
admin.site.register(Inventory)
admin.site.register(InventoryLog)
