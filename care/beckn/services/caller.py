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
import threading

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10


def _post_callback(url: str, callback_action: str, payload: dict) -> None:
    """Blocking POST executed inside a background thread."""
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


def deliver_callback(callback_action: str, payload: dict) -> bool:
    """Fire-and-forget: spawn a daemon thread to POST the ``on_*`` payload.

    The thread is started **before** the caller returns so the ACK reaches ONIX
    immediately, avoiding the 502 that occurs when delivery blocks the response.
    Returns ``True`` when a caller URL is configured (delivery mode), ``False``
    when no caller is configured (direct mode).
    """
    base_url = getattr(settings, "BECKN_BPP_CALLER_URL", None)
    if not base_url:
        return False
    url = f"{base_url.rstrip('/')}/{callback_action}"
    thread = threading.Thread(
        target=_post_callback,
        args=(url, callback_action, payload),
        daemon=True,
        name=f"beckn-callback-{callback_action}",
    )
    thread.start()
    return True
