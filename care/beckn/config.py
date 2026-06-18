"""Configuration helpers for the Beckn integration.

The BPP webhook must attach inbound referrals to a Care ``Facility`` (the
``ResourceRequest.origin_facility`` field is required). The facility is resolved
per-request from the inbound payload (the facility ``external_id`` sent by the
BAP), falling back to a configurable default. The patient's geo organization is
derived from the resolved facility.
"""

from care.facility.models import Facility


def _facility_by_external_id(external_id) -> Facility | None:
    if not external_id:
        return None
    return Facility.objects.filter(external_id=external_id).first()


def _facility_external_id_candidates(context: dict, message: dict) -> list:
    context = context or {}
    attributes = ((message or {}).get("contract", {}) or {}).get(
        "contractAttributes", {}
    ) or {}
    return [
        context.get("facilityId"),
        attributes.get("facilityId"),
        attributes.get("originFacilityId"),
    ]


def _resolve_facility(context: dict, message: dict) -> Facility | None:
    for external_id in _facility_external_id_candidates(context, message):
        facility = _facility_by_external_id(external_id)
        if facility:
            return facility
    return None


def resolve_origin_facility(context: dict, message: dict) -> Facility | None:
    """Resolve the originating facility for an inbound referral (T1).

    The Care facility ``external_id`` is read from the inbound payload, in order:

    1. ``context.facilityId``
    2. ``message.contract.contractAttributes.facilityId``
    3. ``message.contract.contractAttributes.originFacilityId``

    Returns ``None`` when no facility id is present in the payload or none
    matches a Care facility; the caller is responsible for handling this.
    """
    return _resolve_facility(context, message)


def resolve_assigned_facility(context: dict, message: dict) -> Facility | None:
    """Resolve the assigned/target facility for a downstream booking (T2).

    Reads the same ``facilityId`` candidates as the origin facility but does
    **not** fall back to a default: when the target facility is unknown the
    referral's ``assigned_facility`` is left unchanged.
    """
    return _resolve_facility(context, message)


def get_default_geo_organization(facility: Facility | None):
    """Geo organization used when creating a patient from a referral."""
    if facility and facility.geo_organization_id:
        return facility.geo_organization
    return None
