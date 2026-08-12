"""BAP receiver endpoint for the Care-as-BAP orchestration flow.

Care drives a Beckn ``discover -> select -> confirm`` exchange as a BAP (for the
Care frontend). The counterparty routes ``on_discover``/``on_select``/
``on_confirm`` callbacks back to this endpoint. Each callback is correlated to
the in-flight transaction by the Beckn ``transactionId`` (the Redis key set when
``discover`` was initiated) and recorded so the frontend poller can advance.

* ``on_discover`` — the BPP routing identifiers are learned here and reused for
  the subsequent ``select``/``confirm``.
* ``on_confirm`` — the flow adapter persists the durable domain object (e.g. a
  ``ResourceRequest`` for the consultation flow).

Authentication is intentionally open (the network layer verifies signatures);
deployments should additionally restrict access by network/IP.
"""

import logging
import uuid

from rest_framework import status as http_status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from care.beckn.builders.outbound import extract_routing
from care.beckn.constants import (
    CONTRACT_STATUS_ACTIVE,
    CONTRACT_STATUS_COMPLETE,
    CONTRACT_STATUS_COMPLETED,
)
from care.beckn.services import txn_store
from care.beckn.services.flows import FlowError, get_adapter

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
        transaction_id = context.get("transactionId")

        logger.info(
            "Beckn BAP receiver <- '%s' (transactionId=%s)", action, transaction_id
        )

        record = txn_store.get_transaction(transaction_id)
        if record is None:
            try:
                self._handle_referral_callback(transaction_id, action, message)
            except Exception:
                logger.exception(
                    "Beckn BAP receiver failed handling referral '%s' for %s",
                    action,
                    transaction_id,
                )
            return Response(_ack(), status=http_status.HTTP_200_OK)

        try:
            self._handle_callback(record, action, context, message)
        except Exception:
            logger.exception(
                "Beckn BAP receiver failed handling '%s' for %s",
                action,
                transaction_id,
            )

        return Response(_ack(), status=http_status.HTTP_200_OK)

    @staticmethod
    def _handle_referral_callback(
        transaction_id: str, action: str, message: dict
    ) -> None:
        """Handle a direct ``ResourceRequest`` referral callback (no Redis txn).

        The outbound referral confirm
        (:func:`care.beckn.tasks.submit_resource_request_referral`) uses the
        request's ``external_id`` as the Beckn ``transactionId``. The CC posts
        ``on_confirm`` (accepted -> ``approved``) and, once the referral is
        fulfilled downstream, ``on_update``/``on_status`` (completed ->
        ``completed``). Correlation is strictly by ``external_id``; an unknown
        or foreign id is a no-op.
        """
        from care.emr.models.resource_request import ResourceRequest
        from care.emr.resources.resource_request.spec import (
            CategoryChoices,
            StatusChoices,
        )

        # external_id is a UUID column; a foreign/expired Redis id (or any
        # non-uuid) can never match, so skip the query to avoid a lookup error.
        try:
            uuid.UUID(str(transaction_id))
        except (ValueError, TypeError):
            logger.warning(
                "Beckn BAP receiver: non-uuid transaction %s (action=%s)",
                transaction_id,
                action,
            )
            return

        resource_request = ResourceRequest.objects.filter(
            external_id=transaction_id,
            category__in=(
                CategoryChoices.other.value,
                CategoryChoices.patient_care.value,
            ),
        ).first()
        if resource_request is None:
            logger.warning(
                "Beckn BAP receiver: no referral for transaction %s (action=%s)",
                transaction_id,
                action,
            )
            return

        contract = (message or {}).get("contract", {}) or {}
        code = ((contract.get("status", {}) or {}).get("code") or "").upper()

        if action == "on_confirm" and code == CONTRACT_STATUS_ACTIVE:
            if resource_request.status == StatusChoices.pending.value:
                resource_request.status = StatusChoices.approved.value
                resource_request.save(update_fields=["status", "modified_date"])
                logger.info(
                    "Beckn on_confirm approved referral %s (status -> approved)",
                    resource_request.external_id,
                )
            return

        if action in ("on_update", "on_status") and code in (
            CONTRACT_STATUS_COMPLETE,
            CONTRACT_STATUS_COMPLETED,
        ):
            if resource_request.status != StatusChoices.completed.value:
                resource_request.status = StatusChoices.completed.value
                resource_request.save(update_fields=["status", "modified_date"])
                logger.info(
                    "Beckn %s completed referral %s (status -> completed)",
                    action,
                    resource_request.external_id,
                )
            return

    @staticmethod
    def _handle_callback(
        record: dict, action: str, context: dict, message: dict
    ) -> None:
        transaction_id = record["transactionId"]
        body = {"context": context, "message": message}

        # Learn the counterparty routing from the discovery reply so the
        # subsequent select/confirm can be addressed to the right BPP.
        if action == "on_discover":
            txn_store.set_routing(transaction_id, extract_routing(context))

        txn_store.record_response(transaction_id, action, body)

        if action == "on_confirm":
            adapter = get_adapter(record["serviceType"])
            try:
                resource_request_id = adapter.on_confirmed(record, message)
            except FlowError:
                logger.exception(
                    "Beckn on_confirm side effect failed for %s", transaction_id
                )
                return
            if resource_request_id:
                txn_store.set_resource_request(transaction_id, resource_request_id)
