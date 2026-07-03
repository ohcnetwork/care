"""Shared context builder for outbound Beckn actions (Care as BAP).

The Care frontend drives ``discover -> select -> confirm`` and Care emits those
actions as a BAP. The counterparty (BPP) identifiers are not known when
``discover`` is broadcast; they are learned from the ``on_discover`` reply and
threaded back in via ``routing`` for the subsequent ``select``/``confirm``.
"""

import uuid

from django.conf import settings
from django.utils import timezone

# Context fields the frontend must NOT override. transactionId/action are fixed
# per call; bapId/bapUri are Care's OWN receiver identity (always from settings)
# so a stale/incorrect value from the client can never mis-route callbacks.
PROTECTED_CONTEXT_KEYS = ("transactionId", "action", "bapId", "bapUri")


def build_context(
    action: str,
    transaction_id: str,
    routing: dict | None = None,
    overrides: dict | None = None,
) -> dict:
    """Build an outbound Beckn ``context`` for ``action``.

    ``routing`` (learned from ``on_discover``) supplies the BPP identifiers when
    known; otherwise the configured coordination-center defaults are used, and
    ``discover`` may legitimately carry no BPP (a broadcast).

    ``overrides`` lets the caller (the Care frontend) supply Beckn context fields
    directly — e.g. ``bppId``/``bppUri`` chosen from the discover catalog,
    ``networkId`` or ``schemaContext`` — taking precedence over the defaults.
    Only non-null values are applied; ``transactionId``/``action`` are fixed.
    """
    routing = routing or {}
    overrides = overrides or {}
    # ``discover`` is a broadcast: it must NOT carry a BPP. Every other action is
    # addressed to a specific BPP (learned routing, else the configured CC).
    is_discover = action == "discover"
    if is_discover:
        bpp_id = routing.get("bppId")
        bpp_uri = routing.get("bppUri")
    else:
        bpp_id = (
            routing.get("bppId") or getattr(settings, "BECKN_CC_BPP_ID", "") or None
        )
        bpp_uri = (
            routing.get("bppUri") or getattr(settings, "BECKN_CC_BPP_URI", "") or None
        )
    context = {
        "networkId": getattr(settings, "BECKN_NETWORK_ID", "") or None,
        "action": action,
        "version": getattr(settings, "BECKN_VERSION", "2.0.0"),
        "bapId": getattr(settings, "BECKN_BAP_ID", "") or None,
        "bapUri": getattr(settings, "BECKN_BAP_URI", "") or None,
        "transactionId": transaction_id,
        "messageId": str(uuid.uuid4()),
        "timestamp": timezone.now().isoformat(),
        "bppId": bpp_id,
        "bppUri": bpp_uri,
    }
    for key, value in overrides.items():
        if key in PROTECTED_CONTEXT_KEYS or value is None:
            continue
        context[key] = value
    # Drop null fields so the outbound context matches the Beckn shape (e.g. a
    # broadcast discover carries no bppId/bppUri).
    return {key: value for key, value in context.items() if value is not None}


def extract_routing(context: dict) -> dict:
    """Pull the BAP/BPP routing identifiers out of an inbound reply context."""
    context = context or {}
    return {
        "bapId": context.get("bapId"),
        "bapUri": context.get("bapUri"),
        "bppId": context.get("bppId"),
        "bppUri": context.get("bppUri"),
    }


def health_service_jsonpath(value: str) -> dict:
    """Build the ONIX JSONPath catalog filter for a ``healthServiceType``."""
    expression = (
        "$.catalogs[*].resources[*] ? "
        f'(@.resourceAttributes.healthServiceType == "{value}")'
    )
    return {"type": "jsonpath", "expression": expression}


def build_discover_intent(query: dict) -> dict:
    """Build the ``message.intent`` for a discover from the frontend query.

    ``query`` fields:
    * ``healthServiceType`` — builds the JSONPath ``filters`` expression;
    * ``textSearch`` — free-text search passed through;
    * ``filters`` — a ready-made filter object (overrides ``healthServiceType``).
    """
    query = query or {}
    intent: dict = {}
    if query.get("textSearch"):
        intent["textSearch"] = query["textSearch"]
    if query.get("filters"):
        intent["filters"] = query["filters"]
    elif query.get("healthServiceType"):
        intent["filters"] = health_service_jsonpath(query["healthServiceType"])
    return intent
