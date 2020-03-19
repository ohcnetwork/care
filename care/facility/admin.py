from django.contrib import admin

from facility.models import (
    Facility,
    FacilityLocation,
    FacilityStaff,
    FacilityVolunteer,
)

admin.site.register(Facility)
admin.site.register(FacilityLocation)
admin.site.register(FacilityStaff)
admin.site.register(FacilityVolunteer)
