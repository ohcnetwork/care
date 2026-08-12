"""BAP receiver endpoint for the Care-as-BAP orchestration flow.

Care drives a Beckn ``discover -> select -> confirm`` exchange as a BAP (for the
Care frontend). The counterparty routes ``on_discover``/``on_select``/
``on_confirm`` callbacks back to this endpoint, where they are correlated to the
in-flight transaction and applied (see
:mod:`care.beckn.services.receiver`). The synchronous response is always an ACK.

Authentication is intentionally open (the network layer verifies signatures);
deployments should additionally restrict access by network/IP.
"""

import logging

from rest_framework import status as http_status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from care.beckn.services.receiver import receive_bap_callback

logger = logging.getLogger(__name__)


def _ack() -> dict:
    return {"message": {"ack": {"status": "ACK"}}}


class BAPReceiverView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        body = request.data or {}
        context = body.get("context", {}) or {}
        message = body.get("message", {}) or {}
        action = kwargs.get("action") or context.get("action")

        logger.info(
            "Beckn BAP receiver <- '%s' (transactionId=%s)",
            action,
            context.get("transactionId"),
        )
        receive_bap_callback(action, context, message)
        return Response(_ack(), status=http_status.HTTP_200_OK)
