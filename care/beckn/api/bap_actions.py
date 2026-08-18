"""Frontend-facing Beckn BAP action endpoints (Care as BAP for the Care FE).

The Care frontend drives a Beckn ``discover -> select -> confirm`` exchange
through these common endpoints and polls :class:`BecknTransactionView` for
progress. State lives in Redis (see :mod:`care.beckn.services.txn_store`); a
``service_type`` selects the flow adapter that owns the payload shapes.

The counterparty (BPP) URLs are not known up front — they are learned from the
``on_discover`` reply (recorded by the BAP receiver) and reused for
``select``/``confirm``.
"""

import logging

from django.conf import settings
from rest_framework import status as http_status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from care.beckn.builders.outbound import PROTECTED_CONTEXT_KEYS, build_context
from care.beckn.services import txn_store
from care.beckn.services.bap_caller import deliver_bap_action
from care.beckn.services.flows import FlowError, get_adapter

logger = logging.getLogger(__name__)

# deliver_bap_action results that mean the action did not reach the network.
_FAILED_DELIVERY = {"nack", "error"}


def _apply_delivery_result(transaction_id: str, result: str, detail: dict) -> None:
    """Reflect a failed delivery in the transaction status + error for the poller."""
    if result == "nack":
        txn_store.set_status(transaction_id, txn_store.STATUS_NACK)
        txn_store.set_error(transaction_id, detail)
    elif result == "error":
        txn_store.set_status(transaction_id, txn_store.STATUS_ERROR)
        txn_store.set_error(transaction_id, detail)


def _persist_selected_routing(transaction_id: str, context_overrides: dict) -> None:
    """Persist BAP/BPP routing the frontend chose from the discover catalog."""
    routing = {
        "bapId": context_overrides.get("bapId"),
        "bapUri": context_overrides.get("bapUri"),
        "bppId": context_overrides.get("bppId"),
        "bppUri": context_overrides.get("bppUri"),
    }
    if any(routing.values()):
        txn_store.set_routing(transaction_id, routing)


def _build_payload(action, transaction_id, record, body, fallback):
    """Build the outbound ``{context, message}`` payload for an action.

    Prefers a passthrough Beckn ``message`` supplied by the frontend (so the FE
    can send the exact intent/contract — including a ``discover`` JSONPath search
    — and any ``context`` overrides such as the ``bppId``/``bppUri`` chosen from
    the catalog). Falls back to the flow adapter (``fallback``) when no
    ``message`` is provided.

    The ``context`` the frontend supplies is remembered on the transaction and
    auto-applied to every later action, so it only needs to be sent once (e.g.
    the selected provider's routing at ``select``).
    """
    request_overrides = body.get("context") or {}
    _persist_selected_routing(transaction_id, request_overrides)
    txn_store.merge_context(transaction_id, request_overrides)
    record = txn_store.get_transaction(transaction_id) or record

    # Effective context: the remembered template, with this request's values
    # taking precedence.
    effective_overrides = {
        **(record.get("context") or {}),
        **{k: v for k, v in request_overrides.items() if v is not None},
    }

    message = body.get("message")
    if message is not None:
        return {
            "context": build_context(
                action, transaction_id, record.get("routing", {}), effective_overrides
            ),
            "message": message,
        }

    payload = fallback()
    for key, value in effective_overrides.items():
        if key in PROTECTED_CONTEXT_KEYS or value is None:
            continue
        payload["context"][key] = value
    return payload


# Actions Care can initiate as a BAP. ``discover`` starts a new transaction;
# the rest operate on an existing one (by transactionId).
BAP_ACTIONS = ("discover", "select", "init", "confirm", "status", "cancel", "update")
_NEW_TRANSACTION_ACTIONS = {"discover"}


def _adapter_fallback(adapter, action, transaction_id, record, body):
    """Build a payload via the flow adapter when no passthrough message is sent.

    Only ``discover``/``select``/``confirm`` have adapter builders; the other
    actions (``init``/``status``/``cancel``/``update``) require the frontend to
    supply the Beckn ``message`` directly.
    """
    if action == "discover":
        return adapter.build_discover(
            transaction_id, record.get("routing", {}), body.get("query") or {}
        )
    if action == "select":
        return adapter.build_select(
            transaction_id, record.get("routing", {}), record, body
        )
    if action == "confirm":
        return adapter.build_confirm(
            transaction_id, record.get("routing", {}), record, body
        )
    msg = f"'message' is required for action '{action}'"
    raise FlowError(msg)


def _create_local_referral(transaction_id: str, payload: dict) -> None:
    """Create the local (origin) ResourceRequest for an outbound referral init.

    The receiving instance creates its own request for the assigned facility;
    here we create the request owned by the local facility carried in the same
    payload, so the referral is also tracked on this side. Best-effort: a payload
    whose facilities all live in other instances simply creates nothing here and
    never blocks the outbound send.
    """
    context = payload.get("context") or {}
    own_bpp_uri = getattr(settings, "BECKN_BPP_URI", "") or None
    # Loopback: when the init targets this instance's own BPP URI, the inbound
    # BPP init handler creates the request. Creating it here too would duplicate
    # it (the request transaction hasn't committed yet, so the BPP side can't see
    # this row and makes its own), so skip and let the BPP handler own it. Match
    # on bppUri, not bppId — the bppId is shared network-wide across instances.
    if own_bpp_uri and context.get("bppUri") == own_bpp_uri:
        logger.info(
            "Beckn init %s: loopback target; local RR left to the BPP handler",
            transaction_id,
        )
        return

    from care.beckn.services.handlers import BecknActionError, _referral_init

    try:
        _referral_init(context, payload.get("message") or {})
    except BecknActionError:
        logger.info(
            "Beckn init %s: no local facility in payload; local RR not created",
            transaction_id,
        )
    except Exception:
        logger.exception(
            "Beckn init %s: failed creating local ResourceRequest", transaction_id
        )


class BecknActionView(APIView):
    """POST /bap/<action>: initiate any Beckn action as a BAP.

    ``discover`` starts a new transaction (requires ``service_type``); every
    other action (``select``/``init``/``confirm``/``status``/``cancel``/
    ``update``) operates on an existing one (requires ``transactionId``). The
    frontend may pass a passthrough Beckn ``message`` (sent as-is) plus a
    ``context`` override (e.g. the ``bppId``/``bppUri`` chosen from the catalog);
    otherwise the flow adapter builds ``discover``/``select``/``confirm``.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, action, *args, **kwargs):
        action = (action or "").lower()
        if action not in BAP_ACTIONS:
            return Response(
                {"detail": f"Unsupported action: {action}"},
                status=http_status.HTTP_400_BAD_REQUEST,
            )
        body = request.data or {}

        if action in _NEW_TRANSACTION_ACTIONS:
            service_type = body.get("service_type") or body.get("serviceType")
            try:
                adapter = get_adapter(service_type)
            except FlowError as exc:
                return Response(
                    {"detail": str(exc)}, status=http_status.HTTP_400_BAD_REQUEST
                )
            record = txn_store.create_transaction(adapter.service_type)
            transaction_id = record["transactionId"]
        else:
            transaction_id = body.get("transactionId") or body.get("transaction_id")
            record = txn_store.get_transaction(transaction_id)
            if record is None:
                return Response(
                    {"detail": "Unknown or expired transaction"},
                    status=http_status.HTTP_404_NOT_FOUND,
                )
            try:
                adapter = get_adapter(record["serviceType"])
            except FlowError as exc:
                return Response(
                    {"detail": str(exc)}, status=http_status.HTTP_400_BAD_REQUEST
                )

        try:
            payload = _build_payload(
                action,
                transaction_id,
                record,
                body,
                lambda: _adapter_fallback(
                    adapter, action, transaction_id, record, body
                ),
            )
        except FlowError as exc:
            return Response(
                {"detail": str(exc)}, status=http_status.HTTP_400_BAD_REQUEST
            )

        # Persist the confirm parameters so the BAP receiver can create the
        # referral (ResourceRequest) when on_confirm arrives.
        if action == "confirm":
            txn_store.set_patient(transaction_id, body)
        # On init, also create the origin ResourceRequest on this instance using
        # the local facility in the payload (the receiving instance creates the
        # assigned-facility request from the same init).
        if action == "init":
            _create_local_referral(transaction_id, payload)
        txn_store.record_request(transaction_id, action, payload)
        result, detail = deliver_bap_action(action, payload)
        _apply_delivery_result(transaction_id, result, detail)
        response = {"transactionId": transaction_id, "result": result}
        if result != "ack":
            response["detail"] = detail
        return Response(response, status=http_status.HTTP_202_ACCEPTED)


class BecknTransactionView(APIView):
    """GET: the common polling endpoint.

    Without a query param it returns the lightweight status record (fast to
    poll): ``status`` + ``routing``/``context`` + ``actions`` (the keys of the
    payloads recorded so far) + ``resourceRequestId``. The frontend keeps polling
    while ``status`` is a request state (``DISCOVER``/``SELECT``/``CONFIRM``/…)
    and stops/acts once it flips to the matching ``on_*`` state (or a terminal
    ``NACK``/``ERROR``).

    With ``?action=<action>`` (e.g. ``on_discover``) it returns just that action's
    stored ``{context, message}`` payload, so the FE fetches only the slice it
    needs instead of the whole exchange.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, transaction_id: str, *args, **kwargs):
        record = txn_store.get_transaction(transaction_id)
        if record is None:
            return Response(
                {"detail": "Unknown or expired transaction"},
                status=http_status.HTTP_404_NOT_FOUND,
            )

        action = request.query_params.get("action")
        if action:
            data = txn_store.get_action(transaction_id, action)
            return Response(
                {
                    "transactionId": transaction_id,
                    "status": record["status"],
                    "action": action.upper(),
                    "ready": data is not None,
                    "data": data,
                },
                status=http_status.HTTP_200_OK,
            )
        return Response(record, status=http_status.HTTP_200_OK)
