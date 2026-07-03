"""Deliver outbound Beckn actions to the BAP caller (Care acting as BAP).

Mirrors :mod:`care.beckn.services.caller` (which delivers BPP callbacks) but for
the BAP side: Care POSTs an action (e.g. ``confirm``) to the ONIX BAP caller
(``{BECKN_BAP_CALLER_URL}/<action>``), which signs and routes it to the target
CC/BPP. Delivery is enabled only when ``BECKN_BAP_CALLER_URL`` is configured.

This is intended to be called from within a Celery task, so it POSTs
synchronously and returns whether delivery was attempted.
"""

import json
import logging
from http import HTTPStatus

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10


def deliver_bap_action(action: str, payload: dict) -> tuple[str, dict]:
    """POST an outbound Beckn ``action`` to the BAP caller.

    Returns ``(result, detail)`` where ``result`` is one of:

    * ``"ack"``     — the BAP caller accepted the action (HTTP 200, ACK);
    * ``"nack"``    — the BAP caller rejected it (non-200 or a NACK body);
    * ``"error"``   — the POST itself failed (network/timeout);
    * ``"skipped"`` — no BAP caller configured (delivery not attempted).

    ``detail`` explains a non-ack result: ``{"reason": ...}`` and, when the
    caller responded, ``{"statusCode": int, "body": <parsed body or text>,
    "error": <Beckn error object if present>}``.
    """
    base_url = getattr(settings, "BECKN_BAP_CALLER_URL", "")
    if not base_url:
        logger.info(
            "Beckn BAP action '%s' skipped: BECKN_BAP_CALLER_URL not configured",
            action,
        )
        return "skipped", {"reason": "BECKN_BAP_CALLER_URL not configured"}
    url = f"{base_url.rstrip('/')}/{action}"
    transaction_id = (payload.get("context", {}) or {}).get("transactionId")
    logger.info(
        "Beckn BAP -> sending '%s' to %s (transactionId=%s)\npayload=%s",
        action,
        url,
        transaction_id,
        json.dumps(payload, default=str),
    )
    try:
        response = requests.post(url, json=payload, timeout=DEFAULT_TIMEOUT)
    except requests.RequestException as exc:
        logger.exception("Beckn BAP action '%s' delivery to %s failed", action, url)
        return "error", {"reason": f"delivery failed: {exc}"}

    logger.info(
        "Beckn BAP <- '%s' response from %s: status=%s body=%s",
        action,
        url,
        response.status_code,
        response.text[:2000],
    )
    try:
        body = response.json()
    except ValueError:
        body = response.text

    detail = {"statusCode": response.status_code, "body": body}
    if isinstance(body, dict) and body.get("error"):
        detail["error"] = body["error"]

    if response.status_code != HTTPStatus.OK:
        return "nack", detail
    message = body.get("message", {}) or {} if isinstance(body, dict) else {}
    ack_status = (
        message.get("status") or (message.get("ack", {}) or {}).get("status") or ""
    ).upper()
    if ack_status == "NACK":
        return "nack", detail
    return "ack", detail
