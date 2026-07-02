from django.urls import path

from care.beckn.api.bap_webhook import BAPReceiverView
from care.beckn.api.webhook import BPPWebhookView

urlpatterns = [
    path("bpp/webhook", BPPWebhookView.as_view(), name="beckn-bpp-webhook"),
    path(
        "bpp/webhook/<str:action>",
        BPPWebhookView.as_view(),
        name="beckn-bpp-webhook-action",
    ),
    path("bap/receiver", BAPReceiverView.as_view(), name="beckn-bap-receiver"),
    path(
        "bap/receiver/<str:action>",
        BAPReceiverView.as_view(),
        name="beckn-bap-receiver-action",
    ),
]
