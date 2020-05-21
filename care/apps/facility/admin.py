from django.contrib import admin
from .models import (
    Ambulance,
    AmbulanceDriver,
    Facility,
    FacilityLocalGovtBody,
    HospitalDoctors,
    FacilityCapacity,
    FacilityStaff,
    FacilityVolunteer,
    Building,
    Room,
    StaffRoomAllocation,
    InventoryItem,
    Inventory,
    InventoryLog,
    FacilityUser
)

admin.site.register(Ambulance)
admin.site.register(AmbulanceDriver)
admin.site.register(Facility)
admin.site.register(FacilityLocalGovtBody)
admin.site.register(HospitalDoctors)
admin.site.register(FacilityCapacity)
admin.site.register(FacilityStaff)
admin.site.register(FacilityVolunteer)
admin.site.register(Building)
admin.site.register(Room)
admin.site.register(StaffRoomAllocation)
admin.site.register(InventoryItem)
admin.site.register(Inventory)
admin.site.register(InventoryLog)
admin.site.register(FacilityUser)
