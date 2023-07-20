from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views import defaults as default_views
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from care.abdm.api.viewsets.auth import (
    AuthNotifyView,
    DiscoverView,
    LinkConfirmView,
    LinkInitView,
    NotifyView,
    OnAddContextsView,
    OnConfirmView,
    OnFetchView,
    OnInitView,
    RequestDataView,
)
from care.abdm.api.viewsets.monitoring import HeartbeatView
from care.abdm.api.viewsets.status import NotifyView as PatientStatusNotifyView
from care.abdm.api.viewsets.status import SMSOnNotifyView
from care.facility.api.viewsets.open_id import OpenIdConfigView
from care.hcx.api.viewsets.listener import (
    ClaimOnSubmitView,
    CommunicationRequestView,
    CoverageElibilityOnCheckView,
    PreAuthOnSubmitView,
)
from care.users.api.viewsets.change_password import ChangePasswordView
from care.users.reset_password_views import (
    ResetPasswordCheck,
    ResetPasswordConfirm,
    ResetPasswordRequestToken,
)
from config import api_router
from config.health_views import MiddlewareAuthenticationVerifyView

from .auth_views import AnnotatedTokenVerifyView, TokenObtainPairView, TokenRefreshView
from .views import home_view

urlpatterns = [
    path("", home_view, name="home"),
    # Django Admin, use {% url 'admin:index' %}
    path(settings.ADMIN_URL, admin.site.urls),
    # Rest API
    path("api/v1/auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
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
    # Hcx Listeners
    path(
        "coverageeligibility/on_check",
        CoverageElibilityOnCheckView.as_view(),
        name="hcx_coverage_eligibility_on_check",
    ),
    path(
        "preauth/on_submit",
        PreAuthOnSubmitView.as_view(),
        name="hcx_pre_auth_on_submit",
    ),
    path(
        "claim/on_submit",
        ClaimOnSubmitView.as_view(),
        name="hcx_claim_on_submit",
    ),
    path(
        "communication/request",
        CommunicationRequestView.as_view(),
        name="hcx_communication_on_request",
    ),
    # Health check urls
    path("middleware/verify", MiddlewareAuthenticationVerifyView.as_view()),
    path(
        ".well-known/openid-configuration",
        OpenIdConfigView.as_view(),
        name="openid-configuration",
    ),
    path("health/", include("healthy_django.urls", namespace="healthy_django")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.ENABLE_ABDM:
    urlpatterns += [
        path("v1.0/patients/", include(api_router.abdm_urlpatterns)),
        path(
            "v0.5/users/auth/on-fetch-modes",
            OnFetchView.as_view(),
            name="abdm_on_fetch_modes_view",
        ),
        path(
            "v0.5/users/auth/on-init",
            OnInitView.as_view(),
            name="abdm_on_init_view",
        ),
        path(
            "v0.5/users/auth/on-confirm",
            OnConfirmView.as_view(),
            name="abdm_on_confirm_view",
        ),
        path(
            "v0.5/users/auth/notify",
            AuthNotifyView.as_view(),
            name="abdm_auth_notify_view",
        ),
        path(
            "v0.5/links/link/on-add-contexts",
            OnAddContextsView.as_view(),
            name="abdm_on_add_context_view",
        ),
        path(
            "v0.5/care-contexts/discover",
            DiscoverView.as_view(),
            name="abdm_discover_view",
        ),
        path(
            "v0.5/links/link/init",
            LinkInitView.as_view(),
            name="abdm_link_init_view",
        ),
        path(
            "v0.5/links/link/confirm",
            LinkConfirmView.as_view(),
            name="abdm_link_confirm_view",
        ),
        path(
            "v0.5/consents/hip/notify",
            NotifyView.as_view(),
            name="abdm_notify_view",
        ),
        path(
            "v0.5/health-information/hip/request",
            RequestDataView.as_view(),
            name="abdm_request_data_view",
        ),
        path(
            "v0.5/patients/status/notify",
            PatientStatusNotifyView.as_view(),
            name="abdm_patient_status_notify_view",
        ),
        path(
            "v0.5/patients/sms/on-notify",
            SMSOnNotifyView.as_view(),
            name="abdm_patient_status_notify_view",
        ),
        path(
            "v0.5/heartbeat",
            HeartbeatView.as_view(),
            name="abdm_monitoring_heartbeat_view",
        ),
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
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path(
            "swagger/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="swagger-ui",
        ),
        path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    ]
