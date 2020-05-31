from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.accounts import views as accounts_views

app_name = "accounts"

routers = SimpleRouter()

routers.register("users", accounts_views.UserViewSet, basename="users")
routers.register("user-types", accounts_views.UserTypeListViewSet, basename="users_types")
routers.register("states", accounts_views.StateListViewSet, basename="state")
routers.register("districts", accounts_views.DistrictListViewSet, basename="district")

urlpatterns = [
    path("login/", accounts_views.LoginView.as_view(), name="login"),
    path("logout/", accounts_views.LogoutView.as_view(), name="logout"),
    path("forgot-password/", accounts_views.ForgotPasswordLinkView.as_view(), name="forgot_password",),
    path(
        "password-reset-confirm/<str:uidb64>/<str:token>/",
        accounts_views.PasswordResetView.as_view(),
        name="password_reset",
    ),
]

urlpatterns += routers.urls
