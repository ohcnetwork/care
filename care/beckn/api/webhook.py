"""BPP webhook endpoint for the Beckn NFH integration.

The ONIX adapter (onix-bpp) validates the request signature and schema, then
routes the inbound action (select/init/confirm/status) to this endpoint as the
configured ``target.url``. Following the Beckn asynchronous pattern, this view
returns only an ACK/NACK synchronously and delivers the actual ``on_*`` callback
asynchronously to the BPP caller (ONIX), which signs and routes it to the BAP.

Authentication is intentionally open: requests are trusted because ONIX has
already verified the upstream signature. Deployments should additionally
restrict access to this endpoint by network/IP.
"""

import logging

from rest_framework import status as http_status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from care.beckn.constants import ACTION_CALLBACK_MAP
from care.beckn.services.caller import deliver_callback
from care.beckn.services.handlers import ACTION_HANDLERS, BecknActionError
from care.beckn.services.receiver import receive_bap_callback

logger = logging.getLogger(__name__)


def _ack() -> dict:
    return {"message": {"ack": {"status": "ACK"}}}


def _nack(code: str, message: str) -> dict:
    return {
        "message": {"ack": {"status": "NACK"}},
        "error": {"type": "DOMAIN-ERROR", "code": code, "message": message},
    }


class BPPWebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        body = request.data or {}
        context = body.get("context", {}) or {}
        message = body.get("message", {}) or {}
        # ONIX routes the action as a trailing path segment (e.g. .../webhook/init);
        # fall back to the context action when called without the suffix.
        action = kwargs.get("action") or context.get("action")

        # Inbound ``on_*`` callbacks are received here when this instance is also
        # the BAP target (e.g. a single-instance/loopback deployment registered
        # as both roles, or a counterparty using the BPP url for both). They
        # belong to a Care-as-BAP exchange, so they are applied to it rather than
        # ACKed into the void, and never generate a further callback.
        if action and action.startswith("on_"):
            logger.info("Received Beckn callback '%s' on the BPP webhook", action)
            receive_bap_callback(action, context, message)
            return Response(_ack(), status=http_status.HTTP_200_OK)

        if action not in ACTION_CALLBACK_MAP:
            return Response(
                _nack("70001", f"Unsupported action: {action}"),
                status=http_status.HTTP_200_OK,
            )

        handler = ACTION_HANDLERS[action]
        try:
            payload = handler(context, message)
        except BecknActionError as exc:
            logger.warning("Beckn action '%s' failed: %s", action, exc)
            return Response(_nack("70002", str(exc)), status=http_status.HTTP_200_OK)
        except Exception:
            logger.exception("Unexpected error handling Beckn action '%s'", action)
            return Response(
                _nack("50000", "Internal error processing the request"),
                status=http_status.HTTP_200_OK,
            )

        # Deliver the on_* callback asynchronously to the BPP caller (ONIX),
        # which signs and routes it to the BAP. The synchronous response is
        # always just an ACK, per the Beckn async pattern.
        deliver_callback(ACTION_CALLBACK_MAP[action], payload)
        return Response(_ack(), status=http_status.HTTP_200_OK)
