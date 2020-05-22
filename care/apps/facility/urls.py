from rest_framework.routers import SimpleRouter

from apps.facility import (
    views as facility_views
)

routers = SimpleRouter()

routers.register('facility', facility_views.FacilityListViewSet, basename='facility')

urlpatterns = routers.urls
