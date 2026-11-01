"""Redis-backed store for in-flight Beckn BAP transactions.

Care acts as a BAP for the Care frontend: the frontend drives a
``discover -> select -> confirm`` exchange through common action endpoints and
polls a single read endpoint for progress. The in-flight state for one exchange
is held here in Redis (the default Django cache), keyed by the Beckn
``transactionId`` generated when ``discover`` is initiated.

Keeping the state in Redis (rather than on a ``ResourceRequest``) avoids
creating a persisted referral for every ``discover``; the durable
``ResourceRequest`` is created only once the exchange is confirmed.

Record shape::

    {
        "transactionId": "<uuid>",
        "serviceType": "consultation",       # drives flow dispatch
        "status": "ON_DISCOVER",             # current lifecycle state
        "routing": {                         # learned from the on_discover reply
            "bapId": ..., "bapUri": ...,
            "bppId": ..., "bppUri": ...,
        },
        "requests":  {"DISCOVER": {...}, "SELECT": {...}, "CONFIRM": {...}},
        "responses": {"ON_DISCOVER": {...}, "ON_SELECT": {...}, "ON_CONFIRM": {...}},
        "patient": {...},                    # captured at confirm
        "resourceRequestId": "<uuid>",       # set once the referral is created
    }
"""

import uuid

from django.core.cache import cache

# Lifecycle states, in order. Request states are the plain actions; response
# states are the corresponding ``on_*`` callbacks. The frontend keeps polling
# while the status is a request state and stops once it flips to the matching
# ``on_*`` state (or a terminal error state).
STATUS_DISCOVER = "DISCOVER"
STATUS_ON_DISCOVER = "ON_DISCOVER"
STATUS_SELECT = "SELECT"
STATUS_ON_SELECT = "ON_SELECT"
STATUS_CONFIRM = "CONFIRM"
STATUS_ON_CONFIRM = "ON_CONFIRM"
STATUS_ON_STATUS = "ON_STATUS"
STATUS_ON_UPDATE = "ON_UPDATE"
STATUS_UPDATE = "UPDATE"
STATUS_ON_CANCEL = "ON_CANCEL"
STATUS_CANCEL = "CANCEL"
STATUS_NACK = "NACK"
STATUS_ERROR = "ERROR"

KEY_PREFIX = "beckn:txn:"
DEFAULT_TTL = 60 * 60 * 24  # 24 hours


def _key(transaction_id: str) -> str:
    return f"{KEY_PREFIX}{transaction_id}"


def _action_key(transaction_id: str, action_key: str) -> str:
    """Per-action cache key, e.g. ``beckn:txn:<id>:ON_DISCOVER``."""
    return f"{KEY_PREFIX}{transaction_id}:{action_key}"


def _normalize(action: str) -> str:
    return (action or "").upper()


def create_transaction(service_type: str) -> dict:
    """Create and persist a new transaction record, returning it.

    The generated ``transactionId`` is the Beckn transaction id used across the
    whole ``discover -> select -> confirm`` exchange and the key the frontend
    polls with. Only lightweight metadata lives on this record; each action's
    request/response payload is stored under its own key (see
    :func:`record_request` / :func:`record_response`) so the frontend can poll
    the small status record and fetch a single slice on demand.
    """
    transaction_id = str(uuid.uuid4())
    record = {
        "transactionId": transaction_id,
        "serviceType": service_type,
        "status": STATUS_DISCOVER,
        "routing": {},
        "context": {},
        # Keys of the per-action payloads recorded so far (e.g. DISCOVER,
        # ON_DISCOVER). The payloads themselves live under _action_key().
        "actions": [],
        "patient": None,
        "resourceRequestId": None,
        "error": None,
    }
    save_transaction(record)
    return record


def get_transaction(transaction_id: str) -> dict | None:
    """Return the lightweight transaction status record, or ``None``."""
    if not transaction_id:
        return None
    return cache.get(_key(transaction_id))


def save_transaction(record: dict, ttl: int = DEFAULT_TTL) -> None:
    """Persist the lightweight transaction status record (refreshing its TTL)."""
    cache.set(_key(record["transactionId"]), record, timeout=ttl)


def get_action(transaction_id: str, action: str) -> dict | None:
    """Return a single action's stored ``{context, message}`` payload.

    ``action`` may be given in any case and as either the request action
    (``discover``) or the callback (``on_discover``); it is upper-cased to the
    stored key.
    """
    if not transaction_id:
        return None
    return cache.get(_action_key(transaction_id, _normalize(action)))


def _record(transaction_id: str, action: str, payload: dict) -> dict | None:
    key = _normalize(action)
    record = get_transaction(transaction_id)
    if record is None:
        return None
    cache.set(_action_key(transaction_id, key), payload, timeout=DEFAULT_TTL)
    if key not in record["actions"]:
        record["actions"].append(key)
    record["status"] = key
    save_transaction(record)
    return record


def record_request(transaction_id: str, action: str, payload: dict) -> dict | None:
    """Store an outbound request payload under its own key and advance status.

    ``action`` (``discover``/``select``/``confirm``/…) is upper-cased to the key
    and becomes the current status.
    """
    return _record(transaction_id, action, payload)


def record_response(transaction_id: str, action: str, payload: dict) -> dict | None:
    """Store an inbound ``on_*`` response under its own key and advance status.

    ``action`` (``on_discover``/``on_select``/``on_confirm``/…) is upper-cased to
    the key and becomes the current status.
    """
    return _record(transaction_id, action, payload)


def set_status(transaction_id: str, status: str) -> dict | None:
    """Set the transaction status (e.g. to a terminal NACK/ERROR)."""
    record = get_transaction(transaction_id)
    if record is None:
        return None
    record["status"] = status
    save_transaction(record)
    return record


def set_error(transaction_id: str, detail: dict) -> dict | None:
    """Store the failure detail (HTTP status + NACK error body) for the poller."""
    record = get_transaction(transaction_id)
    if record is None:
        return None
    record["error"] = detail
    save_transaction(record)
    return record


def merge_context(transaction_id: str, overrides: dict) -> dict | None:
    """Merge Beckn ``context`` fields into the transaction's stored template.

    The frontend selects context (e.g. ``networkId``, ``bppId``/``bppUri`` from
    the discover catalog, ``schemaContext``) once; it is remembered here and
    auto-applied to every subsequent action so it need not be resent.
    ``transactionId``/``action`` are never stored (they are per-action).
    """
    record = get_transaction(transaction_id)
    if record is None:
        return None
    context = record.setdefault("context", {})
    context.update(
        {
            key: value
            for key, value in (overrides or {}).items()
            if value is not None
            and key not in ("transactionId", "action", "bapId", "bapUri")
        }
    )
    save_transaction(record)
    return record


def set_routing(transaction_id: str, routing: dict) -> dict | None:
    """Merge learned BAP/BPP routing identifiers into the record.

    The counterparty URLs are not known up front; they are read from the
    ``on_discover`` reply context and reused to route ``select``/``confirm``.
    """
    record = get_transaction(transaction_id)
    if record is None:
        return None
    record.setdefault("routing", {}).update(
        {k: v for k, v in routing.items() if v is not None}
    )
    save_transaction(record)
    return record


def set_patient(transaction_id: str, patient: dict) -> dict | None:
    """Store the patient payload captured at confirm time."""
    record = get_transaction(transaction_id)
    if record is None:
        return None
    record["patient"] = patient
    save_transaction(record)
    return record


def set_resource_request(transaction_id: str, resource_request_id: str) -> dict | None:
    """Link the created ``ResourceRequest`` (by external id) to the transaction."""
    record = get_transaction(transaction_id)
    if record is None:
        return None
    record["resourceRequestId"] = resource_request_id
    save_transaction(record)
    return record


# ---------------------------------------------------------------------------
# Booking -> referral link (Beckn appointment flow)
# ---------------------------------------------------------------------------
# When an appointment is booked over Beckn for a referral, the referral's
# coordination id is stored here keyed by the booking id, instead of on the
# booking model, so no core scheduling code is touched. The appointment may be
# fulfilled much later, so this link uses a long TTL.
BOOKING_LINK_PREFIX = "beckn:booking-referral:"
BOOKING_LINK_TTL = 60 * 60 * 24 * 90  # 90 days


def _booking_key(booking_id) -> str:
    return f"{BOOKING_LINK_PREFIX}{booking_id}"


def link_booking_referral(booking_id, coordination_id: str | None) -> None:
    """Remember which referral (by coordination id) a booking was created for."""
    if not (booking_id and coordination_id):
        return
    cache.set(_booking_key(booking_id), coordination_id, timeout=BOOKING_LINK_TTL)


def get_booking_referral(booking_id) -> str | None:
    """Return the referral coordination id linked to a booking, if any."""
    if not booking_id:
        return None
    return cache.get(_booking_key(booking_id))
