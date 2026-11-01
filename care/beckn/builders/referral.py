"""Builders for the NFH referral lifecycle callbacks.

These produce Beckn core v2.0 ``contract`` callback payloads for the BPP. The
BPP largely echoes the inbound contract back to the BAP, overriding the
contract status code and the NFH ``lifecycleState`` to reflect the current
state of the corresponding Care ``ResourceRequest``.
"""

import copy

from care.beckn.builders.context import build_callback_context
from care.beckn.constants import (
    CONTRACT_STATUS_ACTIVE,
    CONTRACT_STATUS_DRAFT,
    HEALTH_REFERRAL_CONTEXT,
    LIFECYCLE_DRAFT,
)
from care.beckn.mappers import map_gender_to_nfh, map_status_to_lifecycle
from care.beckn.services.identifiers import health_ids_from_patient


def _set_contract_status(contract: dict, code: str) -> None:
    contract.setdefault("status", {})
    contract["status"]["code"] = code


def _set_lifecycle_state(contract: dict, lifecycle_state: str) -> None:
    attributes = contract.setdefault("contractAttributes", {})
    attributes.setdefault("@context", HEALTH_REFERRAL_CONTEXT)
    attributes.setdefault("@type", "hrf:HealthReferral")
    attributes["lifecycleState"] = lifecycle_state


def _inject_referral(contract: dict, resource_request) -> None:
    """Expose the Care ``ResourceRequest`` on the callback contract.

    The contract ``id`` is set to the referral's external id and a ``referral``
    block is added under ``contractAttributes`` carrying the Care-side state so
    the BAP receives the actual referral record (not just the echoed request).
    """
    if resource_request is None:
        return
    referral = {
        "id": str(resource_request.external_id),
        "status": resource_request.status,
        "title": resource_request.title,
        "reason": resource_request.reason,
        "emergency": resource_request.emergency,
        "priority": resource_request.priority,
        "category": resource_request.category,
    }
    if resource_request.origin_facility_id:
        referral["originFacilityId"] = str(resource_request.origin_facility.external_id)
    if resource_request.related_patient_id:
        patient = resource_request.related_patient
        referral["patient"] = {
            "id": str(patient.external_id),
            "name": patient.name,
            "gender": map_gender_to_nfh(patient.gender),
        }
        health_ids = health_ids_from_patient(patient)
        if health_ids:
            referral["patient"]["healthIds"] = health_ids
    attributes = contract.setdefault("contractAttributes", {})
    attributes["referral"] = referral


def _strip_pricing(contract: dict) -> None:
    """Remove price/quote/consideration fields (Care referrals carry no cost)."""
    contract.pop("consideration", None)
    contract.pop("quote", None)
    for commitment in contract.get("commitments", []) or []:
        offer = commitment.get("offer")
        if isinstance(offer, dict):
            offer.pop("considerations", None)
        commitment.pop("considerations", None)


def build_on_select(inbound_context: dict, inbound_message: dict) -> dict:
    """Echo the selected contract back (no state change, no pricing)."""
    message = copy.deepcopy(inbound_message or {})
    contract = message.get("contract")
    if isinstance(contract, dict):
        _strip_pricing(contract)
    return {
        "context": build_callback_context(inbound_context, "on_select"),
        "message": message,
    }


def build_booking_callback(
    inbound_context: dict,
    inbound_message: dict,
    callback_action: str,
    contract_status: str,
) -> dict:
    """Build a downstream booking (T2) callback.

    The T2 contract is an ``hct:HealthContract`` (not a HealthReferral), so the
    inbound contract is echoed and only the contract ``status.code`` is set;
    ``contractAttributes`` are left untouched to preserve schema validity.
    """
    message = copy.deepcopy(inbound_message or {})
    contract = message.setdefault("contract", {})
    _set_contract_status(contract, contract_status)
    _strip_pricing(contract)
    return {
        "context": build_callback_context(inbound_context, callback_action),
        "message": message,
    }


def build_on_init(
    inbound_context: dict, inbound_message: dict, resource_request
) -> dict:
    """Build the ``on_init`` callback for a freshly created referral (DRAFT)."""
    message = copy.deepcopy(inbound_message or {})
    contract = message.setdefault("contract", {})
    _set_contract_status(contract, CONTRACT_STATUS_DRAFT)
    _set_lifecycle_state(
        contract, map_status_to_lifecycle(getattr(resource_request, "status", None))
    )
    _inject_referral(contract, resource_request)
    _strip_pricing(contract)
    return {
        "context": build_callback_context(inbound_context, "on_init"),
        "message": message,
    }


def build_on_confirm(
    inbound_context: dict, inbound_message: dict, resource_request
) -> dict:
    """Build the ``on_confirm`` callback for an approved referral (ACTIVE)."""
    message = copy.deepcopy(inbound_message or {})
    contract = message.setdefault("contract", {})
    _set_contract_status(contract, CONTRACT_STATUS_ACTIVE)
    _set_lifecycle_state(
        contract, map_status_to_lifecycle(getattr(resource_request, "status", None))
    )
    _inject_referral(contract, resource_request)
    _strip_pricing(contract)
    return {
        "context": build_callback_context(inbound_context, "on_confirm"),
        "message": message,
    }


def build_on_status(
    inbound_context: dict, inbound_message: dict, resource_request
) -> dict:
    """Build the ``on_status`` callback from the stored referral state.

    The contract snapshot persisted on the referral at confirm time is used as
    the base (falling back to the inbound message), with the contract status
    and ``lifecycleState`` refreshed from the current Care status.
    """
    extensions = getattr(resource_request, "extensions", {}) or {}
    stored = extensions.get("beckn", {}).get("contract")
    if stored:
        message = {"contract": copy.deepcopy(stored)}
    else:
        message = copy.deepcopy(inbound_message or {})
    contract = message.setdefault("contract", {})

    lifecycle_state = map_status_to_lifecycle(getattr(resource_request, "status", None))
    contract_status = (
        CONTRACT_STATUS_DRAFT
        if lifecycle_state == LIFECYCLE_DRAFT
        else CONTRACT_STATUS_ACTIVE
    )
    _set_contract_status(contract, contract_status)
    _set_lifecycle_state(contract, lifecycle_state)
    _inject_referral(contract, resource_request)
    _strip_pricing(contract)
    return {
        "context": build_callback_context(inbound_context, "on_status"),
        "message": message,
    }
