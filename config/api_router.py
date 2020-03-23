from django.conf import settings
from rest_framework.routers import DefaultRouter, SimpleRouter

from care.facility.api.viewsets.ambulance import AmbulanceViewSet
from care.facility.api.viewsets.facility import FacilityViewSet
from care.users.api.views import UserViewSet

if settings.DEBUG:
    router = DefaultRouter()
else:
    router = SimpleRouter()

router.register("users", UserViewSet)
router.register("facility", FacilityViewSet)
router.register("ambulance", AmbulanceViewSet)

app_name = "api"
urlpatterns = router.urls
