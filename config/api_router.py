from django.conf import settings
from rest_framework.routers import DefaultRouter, SimpleRouter

from care.users.api.views import UserViewSet
from care.facility.api.views import FacilityViewSet

if settings.DEBUG:
    router = DefaultRouter()
else:
    router = SimpleRouter()

router.register("users", UserViewSet)
router.register("facility", FacilityViewSet)


app_name = "api"
urlpatterns = router.urls
