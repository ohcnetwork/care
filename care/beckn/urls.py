from django.urls import path

from care.beckn.api.webhook import BPPWebhookView

urlpatterns = [
    path("bpp/webhook", BPPWebhookView.as_view(), name="beckn-bpp-webhook"),
    path(
        "bpp/webhook/<str:action>",
        BPPWebhookView.as_view(),
        name="beckn-bpp-webhook-action",
    ),
]
