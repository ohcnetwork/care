from django.urls import path, re_path

from care.beckn.api.bap_actions import BecknActionView, BecknTransactionView
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
    # Frontend-facing BAP orchestration (Care as BAP for Care FE).
    path(
        "bap/transaction/<str:transaction_id>",
        BecknTransactionView.as_view(),
        name="beckn-bap-transaction",
    ),
    # An ``on_*`` posted to the frontend action path is a counterparty callback,
    # not a frontend action — a counterparty that advertised the plain BAP url
    # instead of ``<url>/receiver`` as its BECKN_BAP_URI. Route it to the
    # receiver, which is unauthenticated, rather than 403-ing or ACKing it into
    # the authenticated action view. Declared before the catch-all below.
    re_path(
        r"^bap/(?P<action>on_[a-z_]+)$",
        BAPReceiverView.as_view(),
        name="beckn-bap-action-callback",
    ),
    # Generic action endpoint: discover/select/init/confirm/status/cancel/update.
    # Declared last so the specific bap/receiver and bap/transaction routes win.
    path("bap/<str:action>", BecknActionView.as_view(), name="beckn-bap-action"),
]
