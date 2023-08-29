from django.urls import path
from rest_framework.routers import SimpleRouter

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
from care.abdm.api.viewsets.hip import HipViewSet
from care.abdm.api.viewsets.monitoring import HeartbeatView
from care.abdm.api.viewsets.status import NotifyView as PatientStatusNotifyView
from care.abdm.api.viewsets.status import SMSOnNotifyView


class OptionalSlashRouter(SimpleRouter):
    def __init__(self):
        super().__init__()
        self.trailing_slash = "/?"


abdm_router = OptionalSlashRouter()

abdm_router.register("profile/v1.0/patients/", HipViewSet, basename="hip")

abdm_urlpatterns = [
    *abdm_router.urls,
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
