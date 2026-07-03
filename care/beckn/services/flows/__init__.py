"""Service-type flow adapters for the Care-as-BAP orchestration.

The frontend calls common ``discover``/``select``/``confirm`` endpoints and
passes a ``service_type``. The service type selects a :class:`FlowAdapter`,
which owns the Beckn payload shapes for that flow and any domain side effect on
confirmation (e.g. creating a ``ResourceRequest`` for the consultation flow).

Register new flows in :data:`REGISTRY`.
"""

from care.beckn.services.flows.appointment import AppointmentFlow
from care.beckn.services.flows.base import FlowAdapter, FlowError
from care.beckn.services.flows.consultation import ConsultationFlow

# service_type -> adapter instance
REGISTRY: dict[str, FlowAdapter] = {
    ConsultationFlow.service_type: ConsultationFlow(),
    AppointmentFlow.service_type: AppointmentFlow(),
}


def get_adapter(service_type: str) -> FlowAdapter:
    """Return the adapter for ``service_type`` or raise :class:`FlowError`."""
    adapter = REGISTRY.get((service_type or "").lower())
    if adapter is None:
        message = f"Unsupported service_type: {service_type!r}"
        raise FlowError(message)
    return adapter


__all__ = ["REGISTRY", "FlowAdapter", "FlowError", "get_adapter"]
