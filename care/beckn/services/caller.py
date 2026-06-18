"""Deliver ``on_*`` callbacks to the BPP caller (ONIX).

In the ONIX adapter model the BPP webhook response is fire-and-forget: ONIX
forwards the inbound action to Care and does **not** route Care's synchronous
response onward. To deliver the callback to the BAP, the BPP app must actively
POST the ``on_*`` payload to the BPP caller endpoint
(e.g. ``http://onix-bpp:8082/bpp/caller/on_init``), which signs it and routes it
to the BAP.

Delivery is enabled only when ``settings.BECKN_BPP_CALLER_URL`` is configured,
so direct-to-Care testing (without ONIX) keeps working unchanged.
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10


def deliver_callback(callback_action: str, payload: dict) -> bool:
    """POST an ``on_*`` payload to the BPP caller, if configured.

    Returns ``True`` when a caller URL is configured and the POST was attempted
    (delivery mode), ``False`` when no caller is configured (direct mode).
    Failures are logged but never raised, so the inbound webhook response is
    unaffected by callback delivery problems.
    """
    base_url = getattr(settings, "BECKN_BPP_CALLER_URL", None)
    if not base_url:
        return False
    url = f"{base_url.rstrip('/')}/{callback_action}"
    try:
        response = requests.post(url, json=payload, timeout=DEFAULT_TIMEOUT)
        logger.info(
            "Delivered Beckn callback '%s' to %s (status %s)",
            callback_action,
            url,
            response.status_code,
        )
    except requests.RequestException:
        logger.exception(
            "Failed to deliver Beckn callback '%s' to %s", callback_action, url
        )
    return True
