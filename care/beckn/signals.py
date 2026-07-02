"""Signals that push Beckn callbacks in response to Care state changes.

When a Beckn-originated ``TokenBooking`` changes status, an unsolicited
``on_status`` callback is delivered to the BAP so it learns the new state
without polling. The previous status is captured in ``pre_save`` and compared in
``post_save`` to fire only on real transitions.

Rescheduling is handled entirely here (no changes to the Care scheduling core):
the Care reschedule flow marks the original booking ``rescheduled`` and then
creates a brand-new replacement booking in the same transaction. We remember the
rescheduled Beckn booking and, when its replacement is created moments later,
carry the Beckn context onto it and notify the BAP (on_status, ACTIVE) with the
new booking's contract id — correlated to the original via the unchanged
``transactionId``.
"""

import contextlib
import logging
import threading

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from care.emr.models.resource_request import ResourceRequest
from care.emr.models.scheduling.booking import TokenBooking
from care.emr.resources.scheduling.slot.spec import BookingStatusChoices

logger = logging.getLogger(__name__)

_PREVIOUS_STATUS_ATTR = "_beckn_previous_status"

# Beckn-originated bookings notify the BAP (via an unsolicited on_status) only
# when they reach one of these lifecycle states through the Care system:
#   - cancel       -> cancelled / entered_in_error
#   - reschedule   -> rescheduled
#   - fulfilment   -> fulfilled
NOTIFY_STATUSES = frozenset(
    {
        BookingStatusChoices.cancelled.value,
        BookingStatusChoices.entered_in_error.value,
        BookingStatusChoices.rescheduled.value,
        BookingStatusChoices.fulfilled.value,
    }
)

# Per-thread queue of Beckn bookings just marked ``rescheduled`` whose
# replacement booking is about to be created in the same request/transaction.
_reschedule_state = threading.local()


def _pending_reschedules() -> list:
    if not hasattr(_reschedule_state, "pending"):
        _reschedule_state.pending = []
    return _reschedule_state.pending


def _clear_pending_reschedules() -> None:
    _reschedule_state.pending = []


def _notifications_suppressed() -> bool:
    return getattr(_reschedule_state, "suppressed", False)


@contextlib.contextmanager
def suppress_beckn_notifications():
    """Within this context, booking status changes do not emit unsolicited
    ``on_status`` callbacks (nor reschedule pairing).

    Used when the change is the direct result of a BAP-initiated action that
    returns its own ``on_*`` callback (e.g. the ``update`` action returns
    ``on_update``), so the BAP is not also told its own contract was cancelled.
    """
    previous = getattr(_reschedule_state, "suppressed", False)
    _reschedule_state.suppressed = True
    try:
        yield
    finally:
        _reschedule_state.suppressed = previous


@receiver(pre_save, sender=TokenBooking, weak=False)
def capture_previous_booking_status(sender, instance, **kwargs):
    """Stash the persisted status before save so post_save can detect a change."""
    if not instance.pk:
        instance.__dict__[_PREVIOUS_STATUS_ATTR] = None
        return
    previous = (
        TokenBooking.objects.filter(pk=instance.pk)
        .values_list("status", flat=True)
        .first()
    )
    instance.__dict__[_PREVIOUS_STATUS_ATTR] = previous


@receiver(post_save, sender=TokenBooking, weak=False)
def notify_beckn_on_status_change(sender, instance, created, **kwargs):
    """Deliver an unsolicited on_status when a Beckn booking is cancelled,
    rescheduled or fulfilled through the Care system.

    Only appointments that originated from a Beckn confirm are notified;
    appointments created directly in Care carry no Beckn transaction context
    and are ignored. Intermediate transitions (e.g. booked -> checked_in) are
    not notified — only the cancel / reschedule / fulfilment lifecycle events.
    """
    previous_status = instance.__dict__.pop(_PREVIOUS_STATUS_ATTR, None)

    if _notifications_suppressed():
        return

    if created:
        # A freshly created booking may be the replacement produced by a
        # reschedule of a Beckn booking; pair it with the remembered original.
        _link_reschedule_replacement(instance)
        return

    if previous_status is None or previous_status == instance.status:
        return
    if instance.status not in NOTIFY_STATUSES:
        return

    # Import lazily to avoid pulling celery into model import time.
    from django.db import transaction

    from care.beckn.tasks import is_beckn_booking, send_appointment_on_status

    if not is_beckn_booking(instance):
        return

    # When a Beckn booking is rescheduled, remember it so the replacement
    # booking (created next in the same transaction) can inherit its context.
    if instance.status == BookingStatusChoices.rescheduled.value:
        _pending_reschedules().append(instance)
        transaction.on_commit(_clear_pending_reschedules)

    booking_id = instance.id
    transaction.on_commit(lambda: send_appointment_on_status.delay(booking_id))


def _link_reschedule_replacement(new_booking):
    """Carry a remembered rescheduled Beckn booking's context onto its
    newly-created replacement and notify the BAP (on_status, ACTIVE)."""
    pending = _pending_reschedules()
    if not pending:
        return
    old_booking = pending.pop(0)

    from care.beckn.tasks import handle_beckn_reschedule

    handle_beckn_reschedule(old_booking, new_booking)


# ---------------------------------------------------------------------------
# Resource request -> outbound BAP confirm (Care as BAP)
# ---------------------------------------------------------------------------

# Categories that route a resource request through the external coordination
# center (CC) via a Beckn confirm instead of the usual in-Care flow.
#   - ``other``        -> GENERAL_PRACTITIONER referral
#   - ``patient_care`` -> FIELD_WORKER referral
BECKN_REFERRAL_CATEGORIES = frozenset({"other", "patient_care"})
# Only newly created requests in this status are referred to the CC.
BECKN_REFERRAL_STATUS = "pending"


@receiver(post_save, sender=ResourceRequest, weak=False)
def initiate_beckn_referral_on_create(sender, instance, created, **kwargs):
    """Send a Beckn ``confirm`` to the CC when a pending resource request in a
    referral category is created.

    Only newly created requests in ``pending`` status whose category is one of
    ``BECKN_REFERRAL_CATEGORIES`` (``other`` or ``patient_care``) are routed to
    the external coordination center; all other resource requests use the usual
    in-Care flow untouched.

    The confirm is sent **synchronously inside the create transaction**: if the
    coordination center rejects it (``nack``) or it cannot be delivered
    (``error``), a ``ValidationError`` is raised so the resource request creation
    is rolled back — the request is not persisted in Care. When no BAP caller is
    configured (``skipped``) the request is created normally.
    """
    if not created:
        return
    if instance.status != BECKN_REFERRAL_STATUS:
        return
    if instance.category not in BECKN_REFERRAL_CATEGORIES:
        return

    from rest_framework.exceptions import ValidationError

    from care.beckn.tasks import submit_resource_request_referral

    result = submit_resource_request_referral(instance)
    if result in ("nack", "error"):
        raise ValidationError(
            "Unable to initiate the referral with the coordination center; "
            "the resource request was not created."
        )
