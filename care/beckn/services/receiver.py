"""Inbound ``on_*`` callback handling for the Care-as-BAP orchestration.

A counterparty callback is correlated to its in-flight exchange by the Beckn
``transactionId`` (the Redis key created when ``discover`` was initiated),
recorded so the frontend poller can advance, and — for ``on_confirm`` — handed
to the flow adapter to persist the durable domain object.

The handling lives here rather than on a view because the same callback can
legitimately arrive at more than one path: its own BAP receiver, the BPP webhook
(a single-instance deployment registered as both roles), or the frontend action
path (a counterparty that advertised the wrong ``BECKN_BAP_URI``).
"""

import logging

from care.beckn.builders.outbound import extract_routing
from care.beckn.services import txn_store
from care.beckn.services.flows import LIFECYCLE_CALLBACKS, FlowError, get_adapter

logger = logging.getLogger(__name__)


def receive_bap_callback(action: str, context: dict, message: dict) -> bool:
    """Apply an inbound callback to its transaction; ``True`` when it was found.

    A callback for an unknown transaction is an in-flight exchange being lost:
    the transaction expired (24h TTL), never existed on this instance, or Redis
    is unavailable — which, with ``IGNORE_EXCEPTIONS`` on the cache, is
    indistinguishable from expiry. The whole callback is logged at error level
    so the exchange can be reconstructed and replayed by hand.
    """
    transaction_id = (context or {}).get("transactionId")
    record = txn_store.get_transaction(transaction_id)
    if record is None:
        logger.error(
            "Beckn callback '%s' dropped: no in-flight transaction %s (expired, "
            "unknown to this instance, or Redis unavailable). Raw callback: %s",
            action,
            transaction_id,
            {"context": context, "message": message},
        )
        return False

    try:
        _apply_callback(record, action, context, message)
    except Exception:
        logger.exception(
            "Beckn BAP receiver failed handling '%s' for %s", action, transaction_id
        )
    return True


def _apply_callback(record: dict, action: str, context: dict, message: dict) -> None:
    transaction_id = record["transactionId"]

    # Learn the counterparty routing from the discovery reply so the subsequent
    # select/confirm can be addressed to the right BPP.
    if action == "on_discover":
        txn_store.set_routing(transaction_id, extract_routing(context))

    txn_store.record_response(
        transaction_id, action, {"context": context, "message": message}
    )

    if action != "on_confirm" and action not in LIFECYCLE_CALLBACKS:
        return

    adapter = get_adapter(record["serviceType"])
    try:
        if action == "on_confirm":
            resource_request_id = adapter.on_confirmed(record, message)
        else:
            # The counterparty reports a state change on an exchange Care has
            # already confirmed; without applying it the local record keeps
            # claiming a state the provider has moved on from.
            resource_request_id = adapter.on_lifecycle(record, action, message)
    except FlowError:
        logger.exception("Beckn '%s' side effect failed for %s", action, transaction_id)
        return
    if resource_request_id:
        txn_store.set_resource_request(transaction_id, resource_request_id)
