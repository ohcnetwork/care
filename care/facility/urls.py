from django.urls import path

from .views import FacilityCreation, FacilityCapacityCreation

app_name = "facility"
urlpatterns = [
    path("create/", FacilityCreation.as_view(), name="facility-create"),
    path(
        "<int:pk>/capacity/add/",
        FacilityCapacityCreation.as_view(),
        name="facility-capacity-create",
    ),
]
