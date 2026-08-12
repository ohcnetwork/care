"""Asynchronous Beckn delivery tasks.

These tasks push unsolicited ``on_*`` callbacks to the BAP (via the BPP caller /
ONIX) in response to internal Care state changes, so the BAP is notified of
booking updates without having to poll the ``status`` action.
"""

import copy
import logging

from celery import shared_task
from django.conf import settings
from django.db import transaction

from care.beckn.builders.catalog import build_appt_on_status
from care.beckn.services.caller import deliver_callback

logger = logging.getLogger(__name__)


def get_booking_beckn_context(booking) -> dict:
    """Return the Beckn block stored on a booking, or an empty dict."""
    return (booking.meta or {}).get("beckn") or {}


def is_beckn_booking(booking) -> bool:
    """True only for bookings that originated from a Beckn confirm.

    Appointments created directly in Care never carry the inbound Beckn
    ``context``/``transactionId`` snapshot, so they are excluded from the
    unsolicited ``on_status`` notifications.
    """
    beckn = get_booking_beckn_context(booking)
    return bool(beckn.get("transactionId") or beckn.get("context"))


def carry_beckn_context(old_booking, new_booking) -> bool:
    """Copy a Beckn booking's stored context onto its replacement booking.

    Returns ``True`` when the context was carried (the source was a Beckn
    booking), making the replacement a first-class Beckn booking.
    """
    if not is_beckn_booking(old_booking):
        return False
    meta = new_booking.meta or {}
    meta["beckn"] = copy.deepcopy(get_booking_beckn_context(old_booking))
    new_booking.meta = meta
    new_booking.save(update_fields=["meta", "modified_date"])
    return True


def handle_beckn_reschedule(old_booking, new_booking) -> None:
    """Carry a rescheduled Beckn booking's context onto its replacement and
    notify the BAP of the new active appointment via on_status.

    The original booking already emits an on_status (rescheduled -> CANCELLED)
    through the status-change signal. Here the stored Beckn context is copied
    onto the newly created booking (so it becomes a first-class Beckn booking)
    and an on_status is pushed for it: ACTIVE, carrying the new booking's
    contract.id, correlated to the BAP via the unchanged transactionId.

    No-op for bookings that did not originate from a Beckn confirm.
    """
    if not carry_beckn_context(old_booking, new_booking):
        return

    new_booking_id = new_booking.id
    transaction.on_commit(lambda: send_appointment_on_status.delay(new_booking_id))


def _routable_context(beckn: dict) -> dict | None:
    """Return a context usable for routing an unsolicited on_status callback.

    Prefer the full inbound context snapshot captured at confirm time. Fall back
    to reconstructing a minimal context from the stored
    ``transactionId``/``bapId``/``bapUri`` (all that older bookings persisted)
    combined with the configured BPP identifiers, so legacy bookings can still
    be routed back to the BAP.
    """
    context = beckn.get("context")
    if context:
        return context

    bap_id = beckn.get("bapId")
    bap_uri = beckn.get("bapUri")
    if not (bap_id and bap_uri):
        return None

    return {
        "transactionId": beckn.get("transactionId"),
        "bapId": bap_id,
        "bapUri": bap_uri,
        "bppId": getattr(settings, "BECKN_BPP_ID", "") or None,
        "bppUri": getattr(settings, "BECKN_BPP_URI", "") or None,
        "networkId": getattr(settings, "BECKN_NETWORK_ID", "") or None,
        "version": getattr(settings, "BECKN_VERSION", "2.0.0"),
    }


@shared_task
def send_appointment_on_status(booking_id: int) -> None:
    """Build and deliver an unsolicited ``on_status`` for a ``TokenBooking``.

    The inbound Beckn ``context`` and ``message`` snapshots captured at confirm
    time are read back from ``booking.meta['beckn']`` and replayed through the
    standard ``on_status`` builder, reflecting the booking's current state.
    Bookings that never originated from a Beckn confirm (no routable context)
    are skipped.
    """
    from care.emr.models.scheduling.booking import TokenBooking

    booking = (
        TokenBooking.objects.filter(id=booking_id)
        .select_related(
            "token_slot",
            "token_slot__resource",
            "token_slot__resource__facility",
            "patient",
        )
        .first()
    )
    if booking is None:
        logger.info("Beckn on_status skipped: booking %s not found", booking_id)
        return

    beckn = get_booking_beckn_context(booking)
    context = _routable_context(beckn)
    if not context:
        logger.info(
            "Beckn on_status skipped for booking %s: no routable BAP context "
            "(stored beckn keys: %s)",
            booking_id,
            sorted(beckn.keys()),
        )
        return

    message = beckn.get("message") or {}
    payload = build_appt_on_status(context, message, booking)
    delivered = deliver_callback("on_status", payload)
    if delivered:
        logger.info(
            "Beckn on_status delivered for booking %s (status=%s)",
            booking_id,
            booking.status,
        )
    else:
        logger.info(
            "Beckn on_status not delivered for booking %s: no caller configured",
            booking_id,
        )


def get_booking_coordination_ref(booking) -> str | None:
    """Return the referral coordination id a booking was created for.

    Read from ``booking.meta['beckn']['coordinationRef']`` (durable, written at
    confirm time) and only then from Redis, which is a fast path that may have
    been evicted — and which, with ``IGNORE_EXCEPTIONS`` on the cache, returns
    ``None`` on a Redis outage rather than raising.
    """
    stored = get_booking_beckn_context(booking).get("coordinationRef")
    if stored:
        return stored

    from care.beckn.services import txn_store

    return txn_store.get_booking_referral(booking.id)


def complete_referral_for_booking(booking) -> None:
    """Mark the originating referral completed when its appointment is fulfilled.

    The booking -> referral link is read from the booking's own Beckn metadata,
    falling back to Redis (see
    :func:`care.beckn.services.txn_store.link_booking_referral`). When the
    booking is fulfilled, the linked ``ResourceRequest`` is transitioned to
    ``completed``. No-op when the booking carries no link or the referral is
    already completed.
    """
    from care.beckn.services.lookup import find_resource_request_by_coordination_id
    from care.emr.resources.resource_request.spec import StatusChoices

    coordination_id = get_booking_coordination_ref(booking)
    if not coordination_id:
        if is_beckn_booking(booking):
            logger.warning(
                "Beckn booking %s fulfilled but carries no referral link; "
                "no referral completed",
                booking.id,
            )
        return

    resource_request = find_resource_request_by_coordination_id(coordination_id)
    if resource_request is None:
        logger.warning(
            "Beckn booking %s fulfilled but no referral matched coordination id %s",
            booking.id,
            coordination_id,
        )
        return
    if resource_request.status == StatusChoices.completed.value:
        return
    resource_request.status = StatusChoices.completed.value
    resource_request.save(update_fields=["status", "modified_date"])
    logger.info(
        "Beckn referral %s marked completed (booking %s fulfilled)",
        resource_request.external_id,
        booking.id,
    )
