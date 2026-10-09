"""Publish the Care catalog to the network via the ONIX BPP caller.

In the ONIX model the BPP advertises its inventory by POSTing a catalog to the
BPP caller ``publish`` action (``catalog/publish``), which signs it and forwards
it to the network Catalog Discovery Service (CDS). The catalog itself is built
from Care facilities and their public practitioner schedules
(see :mod:`care.beckn.services.catalog`).

The published payload follows the network-management contract:

* ``context.action`` is ``catalog/publish`` with ``bppId``/``bppUri`` (no
  ``bapId``) and the ``networkId``;
* ``message.catalogs[]`` carries the catalogs, each repeating ``bppId``/
  ``bppUri``;
* ``message.publishDirectives[]`` carries one directive per catalog.
"""

import logging
import uuid

import requests
from django.conf import settings
from django.utils import timezone

from care.beckn.services.catalog import build_catalogs, build_coordination_catalog

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 15


def build_publish_context() -> dict:
    """Build the Beckn ``catalog/publish`` context from configured BPP identity."""
    return {
        "networkId": getattr(settings, "BECKN_NETWORK_ID", "") or None,
        "action": "catalog/publish",
        "version": getattr(settings, "BECKN_VERSION", "2.0.0"),
        "bppId": getattr(settings, "BECKN_BPP_ID", "") or None,
        "bppUri": getattr(settings, "BECKN_BPP_URI", "") or None,
        "transactionId": str(uuid.uuid4()),
        "messageId": str(uuid.uuid4()),
        "timestamp": timezone.now().isoformat(),
    }


def build_publish_payload(public_only: bool = True, coordination: bool = False) -> dict:
    """Return the full ``{context, message}`` ``catalog/publish`` payload.

    ``coordination=True`` publishes the Care-coordinator ("front desk")
    ``ServiceCoordinationResource`` catalog instead of the facility/practitioner
    ``HealthResource`` catalogs.
    """
    bpp_id = getattr(settings, "BECKN_BPP_ID", "") or None
    bpp_uri = getattr(settings, "BECKN_BPP_URI", "") or None
    network_id = getattr(settings, "BECKN_NETWORK_ID", "") or None

    if coordination:
        catalogs = [build_coordination_catalog()]
    else:
        catalogs = build_catalogs(public_only=public_only)
    directives = []
    for catalog in catalogs:
        # Each catalog repeats the publisher identity per the publish contract.
        catalog["bppId"] = bpp_id
        catalog["bppUri"] = bpp_uri
        directives.append(
            {
                "catalogId": catalog["id"],
                "catalogType": "REGULAR",
                "updateMode": "FULL",
                "visibleTo": [network_id] if network_id else [],
            }
        )

    return {
        "context": build_publish_context(),
        "message": {
            "catalogs": catalogs,
            "publishDirectives": directives,
        },
    }


def publish_catalog(
    public_only: bool = True, dry_run: bool = False, coordination: bool = False
) -> dict:
    """Build and (unless ``dry_run``) POST the catalog to the BPP caller.

    ``coordination=True`` publishes the Care-coordinator ("front desk") catalog.
    Returns a small result dict describing the outcome. Raises
    ``RuntimeError`` when no BPP caller URL is configured and not a dry run.
    """
    payload = build_publish_payload(public_only=public_only, coordination=coordination)
    catalog_count = len(payload["message"]["catalogs"])

    if dry_run:
        return {"status": "dry_run", "catalogs": catalog_count, "payload": payload}

    base_url = getattr(settings, "BECKN_BPP_CALLER_URL", "")
    if not base_url:
        raise RuntimeError(
            "BECKN_BPP_CALLER_URL is not configured; cannot publish catalog"
        )
    url = f"{base_url.rstrip('/')}/publish"
    response = requests.post(url, json=payload, timeout=DEFAULT_TIMEOUT)
    logger.info(
        "Published Beckn catalog (%d catalogs) to %s (status %s)",
        catalog_count,
        url,
        response.status_code,
    )
    return {
        "status": "published",
        "catalogs": catalog_count,
        "url": url,
        "http_status": response.status_code,
        "response": response.text[:2000],
    }
