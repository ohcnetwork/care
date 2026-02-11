from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views import defaults as default_views
from django.views.decorators.cache import cache_page
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from care.users.api.viewsets.change_password import ChangePasswordView
from care.users.reset_password_views import (
    ResetPasswordCheck,
    ResetPasswordConfirm,
    ResetPasswordRequestToken,
)
from config import api_router

from .auth_views import (
    AnnotatedTokenVerifyView,
    LogoutView,
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import app_version, home_view, ping

urlpatterns = [
    path("", home_view, name="home"),
    path("ping/", ping, name="ping"),
    path("health/", include("healthy_django.urls", namespace="healthy_django")),
    path("app_version/", app_version, name="app_version"),
    path(f"{settings.ADMIN_URL.rstrip('/')}/", admin.site.urls),
    path("api/v1/auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/logout/", LogoutView.as_view(), name="token_obtain_pair"),
    path(
        "api/v1/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"
    ),
    path(
        "api/v1/auth/token/verify/",
        AnnotatedTokenVerifyView.as_view(),
        name="token_verify",
    ),
    path(
        "api/v1/password_reset/",
        ResetPasswordRequestToken.as_view(),
        name="password_reset_request",
    ),
    path(
        "api/v1/password_reset/confirm/",
        ResetPasswordConfirm.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "api/v1/password_reset/check/",
        ResetPasswordCheck.as_view(),
        name="password_reset_check",
    ),
    path(
        "api/v1/password_change/",
        ChangePasswordView.as_view(),
        name="change_password_view",
    ),
    path("api/v1/", include(api_router.urlpatterns)),
    *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
]

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        urlpatterns += [path("__debug__/", include("debug_toolbar.urls"))]

    if "silk" in settings.INSTALLED_APPS:
        urlpatterns += [path("silk/", include("silk.urls", namespace="silk"))]

if settings.DEBUG or not settings.IS_PRODUCTION:
    urlpatterns += [
        path(
            "api/schema/",
            cache_page(None, cache="swagger_cache")(SpectacularAPIView.as_view()),
            name="schema",
        ),
        path(
            "swagger/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="swagger-ui",
        ),
        path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    ]

for plug in settings.PLUGIN_APPS:
    urlpatterns += [path(f"api/{plug}/", include(f"{plug}.urls"))]
