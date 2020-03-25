from django.urls import path

from .views import (
    DoctorCountCreation,
    DoctorCountUpdation,
    FacilitiesView,
    FacilityCapacityCreation,
    FacilityCapacityUpdation,
    FacilityCreation,
    FacilityUpdation,
    FacilityView,
)

app_name = "facility"
urlpatterns = [
    path("create/", FacilityCreation.as_view(), name="facility-create"),
    path("", FacilitiesView.as_view(), name="facilities-view"),
    path("<int:pk>", FacilityView.as_view(), name="facility-view"),
    path("<int:pk>/update", FacilityUpdation.as_view(), name="facility-update"),
    path("<int:pk>/capacity/add/", FacilityCapacityCreation.as_view(), name="facility-capacity-create",),
    path("<int:fpk>/capacity/<int:cpk>/", FacilityCapacityUpdation.as_view(), name="facility-capacity-update",),
    path("<int:pk>/doctorcount/add/", DoctorCountCreation.as_view(), name="facility-doctor-count-create",),
    path("<int:fpk>/doctorcount/<int:cpk>/", DoctorCountUpdation.as_view(), name="facility-doctor-count-update",),
]
