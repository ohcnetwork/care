from django.urls import path

from .views import (
    FacilityCreation,
    FacilityCapacityCreation,
    FacilitiesView,
    FacilityView,
    FacilityCapacityUpdation,
)

app_name = "facility"
urlpatterns = [
    path("create/", FacilityCreation.as_view(), name="facility-create"),
    path("", FacilitiesView.as_view(), name="facilities-view"),
    path("<int:pk>", FacilityView.as_view(), name="facility-view"),
    path(
        "<int:pk>/capacity/add/",
        FacilityCapacityCreation.as_view(),
        name="facility-capacity-create",
    ),
    path(
        "<int:fpk>/capacity/<int:cpk>/",
        FacilityCapacityUpdation.as_view(),
        name="facility-capacity-update",
    ),
]
