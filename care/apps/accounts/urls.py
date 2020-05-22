from rest_framework.routers import SimpleRouter

from apps.accounts import views as accounts_views

routers = SimpleRouter()

routers.register('users', accounts_views.UserViewSet, basename='users')

urlpatterns = routers.urls
