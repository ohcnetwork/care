from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.accounts import views as accounts_views

routers = SimpleRouter()

routers.register('users', accounts_views.UserViewSet, basename='users')
routers.register('states', accounts_views.StateListViewSet, basename='state')
routers.register('districts', accounts_views.DistrictListViewSet, basename='district')

urlpatterns = [
    path('login/', accounts_views.LoginView.as_view(), name='login'),
    path('logout/', accounts_views.LogoutView.as_view(), name='logout')
]

urlpatterns += routers.urls
