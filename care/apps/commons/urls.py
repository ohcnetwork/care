from rest_framework.routers import SimpleRouter

from apps.commons import views as commons_views

routers = SimpleRouter()

routers.register("ownership-type", commons_views.OwnershiptTypeViewSet, basename="ownership_type")

urlpatterns = routers.urls
