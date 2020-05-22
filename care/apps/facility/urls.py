from django.urls import path

from apps.facility import (
    views as facility_views
)

urlpatterns = [
    path('list/', facility_views.FacilityListView.as_view())
]
