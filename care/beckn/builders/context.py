"""Builders for the Beckn callback ``context`` block.

The BPP echoes the inbound context back to the BAP, preserving the
``transactionId`` for correlation while minting a fresh ``messageId`` and
``timestamp`` for the callback and swapping the action to its ``on_*`` form.
"""

import uuid

from django.utils import timezone


def build_callback_context(inbound_context: dict, callback_action: str) -> dict:
    """Build the callback context from the inbound request context.

    - ``transactionId`` is preserved (referral correlation).
    - ``messageId`` is regenerated for the callback.
    - ``timestamp`` is set to now.
    - ``action`` is set to the ``on_*`` callback action.
    - All routing identifiers (bapId/bapUri/bppId/bppUri/networkId/version/
      schemaContext) are echoed unchanged so the ONIX caller can sign and
      route the response.
    """
    context = dict(inbound_context or {})
    context["action"] = callback_action
    context["messageId"] = str(uuid.uuid4())
    context["timestamp"] = timezone.now().isoformat()
    return context
