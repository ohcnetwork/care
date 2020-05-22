from rest_framework.routers import SimpleRouter

from apps.facility import (
    views as facility_views
)

routers = SimpleRouter()

routers.register('list', facility_views.FacilityListView, basename='facility')

urlpatterns = routers.urls
