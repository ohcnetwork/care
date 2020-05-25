from rest_framework.routers import SimpleRouter

from apps.facility import views as facility_views

routers = SimpleRouter()

routers.register("facility", facility_views.FacilityViewSet, basename="facility")
routers.register(
    "facility-users", facility_views.FacilityUserViewSet, basename="facility_user"
)
routers.register("inventories", facility_views.InventoryViewSet, basename="inventory")
routers.register("staffs", facility_views.FacilityStaffViewSet, basename="staffs")
routers.register(
    "infrastructures",
    facility_views.FacilityInfrastructureViewSet,
    basename="infrastructure",
)

urlpatterns = routers.urls
