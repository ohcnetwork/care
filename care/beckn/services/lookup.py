"""Locate the Care ``ResourceRequest`` for an inbound Beckn referral.

Correlation identifiers are persisted on ``ResourceRequest.extensions`` at init
time and used to locate the referral on subsequent ``confirm``/``status``
callbacks. The downstream booking (T2) references the same referral via
``coordinationRef`` (== the T1 ``coordinationId``), so both resolve here.
"""

from care.beckn.mappers import get_coordination_id
from care.emr.models.resource_request import ResourceRequest


def find_resource_request_by_coordination_id(
    coordination_id: str | None,
) -> ResourceRequest | None:
    """Find the referral whose stored Beckn ``coordinationId`` matches."""
    if not coordination_id:
        return None
    return ResourceRequest.objects.filter(
        extensions__beckn__coordinationId=coordination_id
    ).first()


def find_resource_request(context: dict, message: dict) -> ResourceRequest | None:
    """Find the referral by coordination id (T1 ``coordinationId`` / T2
    ``coordinationRef``), then by transaction id."""
    coordination_id = get_coordination_id(context, message)
    transaction_id = (context or {}).get("transactionId")

    if coordination_id:
        request = ResourceRequest.objects.filter(
            extensions__beckn__coordinationId=coordination_id
        ).first()
        if request:
            return request

    if transaction_id:
        request = ResourceRequest.objects.filter(
            extensions__beckn__transactionId=transaction_id
        ).first()
        if request:
            return request
    return None
