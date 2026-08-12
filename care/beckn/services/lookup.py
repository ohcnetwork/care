"""Locate the Care ``ResourceRequest`` for an inbound Beckn referral.

Correlation identifiers are persisted on ``ResourceRequest.extensions`` at init
time and used to locate the referral on subsequent ``confirm``/``status``
callbacks. The downstream booking (T2) references the same referral via
``coordinationRef`` (== the T1 ``coordinationId``), so both resolve here.
"""

from django.core.exceptions import ValidationError

from care.beckn.mappers import get_contract
from care.emr.models.resource_request import ResourceRequest


def find_resource_request_by_external_id(
    external_id: str | None,
) -> ResourceRequest | None:
    """Find the referral whose Care ``external_id`` matches the contract id.

    The ``on_init`` callback publishes the created referral's ``external_id`` as
    the contract ``id``; the BAP echoes it back on ``confirm``/``status`` so the
    BPP can resolve the exact referral record.
    """
    if not external_id:
        return None
    try:
        return ResourceRequest.objects.filter(external_id=external_id).first()
    except (ValueError, ValidationError):
        return None


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
    """Find the referral by contract id, then by coordination / transaction id.

    ``on_init`` publishes the created referral's ``external_id`` as the contract
    ``id``. When the BAP does not echo it back on ``confirm``/``status`` (it
    keeps its own contract id), fall back to the stable ``coordinationId`` (T1)
    / ``coordinationRef`` (T2) and finally the Beckn ``transactionId``, both
    persisted on ``extensions['beckn']`` at init — so the same referral is
    approved in place instead of a duplicate being created.
    """
    from care.beckn.mappers import get_coordination_id

    request = find_resource_request_by_external_id(get_contract(message).get("id"))
    if request is not None:
        return request

    request = find_resource_request_by_coordination_id(
        get_coordination_id(context, message)
    )
    if request is not None:
        return request

    transaction_id = (context or {}).get("transactionId")
    if transaction_id:
        return ResourceRequest.objects.filter(
            extensions__beckn__transactionId=transaction_id
        ).first()
    return None
