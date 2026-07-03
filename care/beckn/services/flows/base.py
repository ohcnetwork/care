"""Base class for Care-as-BAP service-type flow adapters."""

from abc import ABC, abstractmethod


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
