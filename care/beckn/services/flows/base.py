"""Base class for Care-as-BAP service-type flow adapters."""

import logging
from abc import ABC, abstractmethod

from care.beckn.constants import (
    CONTRACT_STATUS_CANCELLED,
    CONTRACT_STATUS_COMPLETE,
    CONTRACT_STATUS_COMPLETED,
    LIFECYCLE_ACTIVE,
    LIFECYCLE_BOOKING_CONFIRMED,
    LIFECYCLE_CANCELLED,
    LIFECYCLE_FULFILLED,
)

logger = logging.getLogger(__name__)

# Callbacks that report a change of state on an exchange Care already confirmed.
LIFECYCLE_CALLBACKS = ("on_status", "on_update", "on_cancel")


class FlowError(Exception):
    """Raised when a flow cannot build a payload or apply a confirmation."""


class FlowAdapter(ABC):
    """Owns the Beckn payloads and confirmation side effect for one service type.

    Concrete adapters build the outbound ``discover``/``select``/``confirm``
    ``{context, message}`` payloads for their flow and, on ``on_confirm``,
    persist whatever domain object represents the confirmed exchange.
    """

    #: The ``service_type`` value this adapter handles (lower-case).
    service_type: str = ""

    @abstractmethod
    def build_discover(self, transaction_id: str, routing: dict, query: dict) -> dict:
        """Build the outbound ``discover`` payload from the frontend query."""

    @abstractmethod
    def build_select(
        self, transaction_id: str, routing: dict, record: dict, params: dict
    ) -> dict:
        """Build the outbound ``select`` payload for the chosen offer.

        ``record`` is the stored transaction (with the ``on_discover`` catalog);
        ``params`` carries the frontend selection (e.g. ``offerId``).
        """

    @abstractmethod
    def build_confirm(
        self, transaction_id: str, routing: dict, record: dict, params: dict
    ) -> dict:
        """Build the outbound ``confirm`` payload carrying patient data."""

    def on_confirmed(self, record: dict, message: dict) -> str | None:
        """Apply the domain side effect for an inbound ``on_confirm``.

        Return the external id of any persisted object (e.g. a
        ``ResourceRequest``) to link it to the transaction, or ``None``.
        Default: no side effect.
        """
        return None

    def on_lifecycle(self, record: dict, action: str, message: dict) -> str | None:
        """Apply an inbound ``on_status``/``on_update``/``on_cancel`` callback.

        These report the counterparty's view of an exchange Care already
        confirmed, so ignoring them leaves the local record claiming a state the
        provider has moved on from. Return the external id of the object the
        callback was applied to, or ``None``. Default: no side effect.
        """
        return None

    @staticmethod
    def _system_user():
        from django.conf import settings

        from care.users.models import User

        username = getattr(settings, "BECKN_SYSTEM_USERNAME", None)
        if username:
            return User.objects.filter(username=username).first()
        return None

    @staticmethod
    def resolve_confirm_facility(record: dict):
        """Resolve the Care facility a confirmed exchange belongs to.

        Read from the frontend's confirm body (``facility``) or, when the
        frontend sent a passthrough Beckn message, from the ``facilityId`` on the
        contract it sent. Returns ``None`` when neither names a Care facility.
        """
        from care.beckn.services import txn_store
        from care.facility.models import Facility

        params = record.get("patient") or {}
        external_id = params.get("facility")
        if not external_id:
            sent_confirm = (
                txn_store.get_action(record.get("transactionId"), "CONFIRM") or {}
            )
            sent_attributes = (sent_confirm.get("message") or {}).get(
                "contract", {}
            ).get("contractAttributes", {}) or {}
            external_id = sent_attributes.get("facilityId")
        if not external_id:
            return None
        return Facility.objects.filter(external_id=external_id).first()

    @classmethod
    def apply_referral_lifecycle(
        cls, referral, action: str, message: dict
    ) -> str | None:
        """Move a referral to the state an inbound lifecycle callback reports.

        A ``DRAFT`` lifecycle state is ignored: it would pull an approved
        referral backwards. A referral Care has already completed is never
        changed, so a late or replayed callback is a no-op.
        """
        from care.emr.resources.resource_request.spec import StatusChoices

        status = cls._status_from_callback(action, message)
        if status is None or referral.status == status:
            return str(referral.external_id)
        if referral.status == StatusChoices.completed.value:
            logger.info(
                "Beckn %s for referral %s ignored: already completed",
                action,
                referral.external_id,
            )
            return str(referral.external_id)

        previous = referral.status
        referral.status = status
        referral.save(update_fields=["status", "modified_date"])
        logger.info(
            "Beckn %s moved referral %s from %s to %s",
            action,
            referral.external_id,
            previous,
            status,
        )
        return str(referral.external_id)

    @staticmethod
    def _status_from_callback(action: str, message: dict) -> str | None:
        """Map an inbound callback's contract state to a Care referral status."""
        from care.emr.resources.resource_request.spec import StatusChoices

        lifecycle_to_status = {
            LIFECYCLE_CANCELLED: StatusChoices.cancelled.value,
            LIFECYCLE_FULFILLED: StatusChoices.completed.value,
            LIFECYCLE_BOOKING_CONFIRMED: StatusChoices.transfer_in_progress.value,
            LIFECYCLE_ACTIVE: StatusChoices.approved.value,
        }

        contract = (message or {}).get("contract", {}) or {}
        code = ((contract.get("status") or {}).get("code") or "").upper()
        attributes = contract.get("contractAttributes", {}) or {}
        lifecycle = (attributes.get("lifecycleState") or "").upper()

        if action == "on_cancel" or code == CONTRACT_STATUS_CANCELLED:
            return StatusChoices.cancelled.value
        if code in (CONTRACT_STATUS_COMPLETED, CONTRACT_STATUS_COMPLETE):
            return StatusChoices.completed.value
        return lifecycle_to_status.get(lifecycle)
