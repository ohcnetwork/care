from django.urls import path

# from care.users.views import (
#     user_detail_view,
#     user_redirect_view,
#     user_update_view,
# )

from django.contrib.auth.views import LogoutView
from .views import SignupView, SinginView

app_name = "users"
urlpatterns = [
    # path("~redirect/", view=user_redirect_view, name="redirect"),
    # path("~update/", view=user_update_view, name="update"),
    # path("<str:username>/", view=user_detail_view, name="detail"),
    path(
        "signup/volunteer/",
        SignupView.as_view(),
        {"type": 20, "name": "Volunteer"},
        name="signup-volunteer",
    ),
    path(
        "signup/doctor/",
        SignupView.as_view(),
        {"type": 5, "name": "Doctor"},
        name="signup-doctor",
    ),
    path(
        "signup/staff/",
        SignupView.as_view(),
        {"type": 10, "name": "Hospital Administrator"},
        name="signup-staff",
    ),
    path("signin/", SinginView.as_view(), name="signin"),
    path("logout/", LogoutView.as_view(), name="logout"),
]
