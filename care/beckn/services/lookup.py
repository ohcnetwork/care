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
    """Find the referral strictly by contract id (== Care ``external_id``).

    The ``on_init`` callback publishes the created referral's ``external_id`` as
    the contract ``id``; the BAP must echo it back on ``confirm``/``status``.
    No coordination/transaction id fallback is applied — if the contract id does
    not resolve to a referral, ``None`` is returned and the caller must error.
    """
    contract_id = get_contract(message).get("id")
    return find_resource_request_by_external_id(contract_id)
