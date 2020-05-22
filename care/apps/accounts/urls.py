from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.accounts import views as accounts_views

routers = SimpleRouter()

routers.register('users', accounts_views.UserViewSet, basename='users')

urlpatterns = [
    path('state/list/', accounts_views.StateListView.as_view(), name='state_list'),
    path('districts/list/', accounts_views.DistrictListView.as_view(), name='district_list'),
    path('login/', accounts_views.LoginView.as_view(), name='login'),
    path('logout/', accounts_views.LogoutView.as_view(), name='logout')
]

urlpatterns += routers.urls
