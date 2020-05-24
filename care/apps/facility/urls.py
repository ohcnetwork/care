from rest_framework.routers import SimpleRouter

from apps.facility import views as facility_views

routers = SimpleRouter()

routers.register("facility", facility_views.FacilityViewSet, basename="facility")
routers.register(
    "facility-users", facility_views.FacilityUserViewSet, basename="facility_user"
)

urlpatterns = routers.urls
