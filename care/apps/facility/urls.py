from rest_framework.routers import SimpleRouter

from apps.facility import views as facility_views

routers = SimpleRouter()

routers.register("facility", facility_views.FacilityViewSet, basename="facility")
routers.register("facility-users", facility_views.FacilityUserViewSet, basename="facility_user")
routers.register("inventories", facility_views.InventoryViewSet, basename="inventory")
routers.register("staffs", facility_views.FacilityStaffViewSet, basename="staffs")
routers.register(
    "infrastructures", facility_views.FacilityInfrastructureViewSet, basename="infrastructure",
)
routers.register("facility-type", facility_views.FacilityTypeViewSet, basename="facility_type")
routers.register("inventories", facility_views.InventoryViewSet, basename="inventory")
routers.register("inventory-items", facility_views.InventoryItemViewSet, basename="inventory_items")
routers.register("room-type", facility_views.RoomTypeViewSet, basename="room_items")
routers.register("bed-type", facility_views.BedTypeViewSet, basename="bed_items")

urlpatterns = routers.urls
