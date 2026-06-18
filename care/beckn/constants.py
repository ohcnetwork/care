"""Constants for the Beckn NFH (DHP) integration.

These mirror the values used by the DHP reference flows and the ONIX adapter
so that payloads produced by Care validate against the Beckn core v2.0 schema
and the NFH JSON-LD healthcare extensions.
"""

# Beckn protocol version used by the ONIX adapter / NFH network.
BECKN_VERSION = "2.0.0"

# JSON-LD contexts for the NFH healthcare extensions.
HEALTH_REFERRAL_CONTEXT = "https://schema.beckn.io/HealthReferral/v2.1/context.jsonld"
HEALTH_PARTICIPANT_CONTEXT = (
    "https://schema.beckn.io/HealthParticipant/v2.1/context.jsonld"
)
HEALTH_OFFER_CONTEXT = "https://schema.beckn.io/HealthOffer/v2.1/context.jsonld"
HEALTH_CONSIDERATION_CONTEXT = (
    "https://schema.beckn.io/HealthConsideration/v2.1/context.jsonld"
)
CODED_VALUE_CONTEXT = (
    "https://raw.githubusercontent.com/beckn/DHP-Specs/main/devkit/stub/context.jsonld"
)

# Inbound Beckn actions routed to the BPP webhook by the ONIX adapter, mapped to
# the callback action returned in the response. Discovery (search/on_search) is
# intentionally excluded for now.
ACTION_CALLBACK_MAP = {
    "select": "on_select",
    "init": "on_init",
    "confirm": "on_confirm",
    "status": "on_status",
}

# Beckn contract status codes.
CONTRACT_STATUS_DRAFT = "DRAFT"
CONTRACT_STATUS_ACTIVE = "ACTIVE"
CONTRACT_STATUS_CANCELLED = "CANCELLED"
CONTRACT_STATUS_COMPLETED = "COMPLETED"
CONTRACT_STATUS_COMPLETE = "COMPLETE"

# contractAttributes.@type discriminators distinguishing the two referral
# transactions that share the select/init/confirm/status endpoints:
#   T1 (referral coordination)  -> hrf:HealthReferral  -> Care ResourceRequest
#   T2 (downstream booking)     -> hct:HealthContract  -> updates the same
#                                  ResourceRequest via coordinationRef.
CONTRACT_TYPE_REFERRAL = "hrf:HealthReferral"
CONTRACT_TYPE_BOOKING = "hct:HealthContract"

# Transaction kinds resolved from an inbound payload.
TXN_REFERRAL = "referral"
TXN_BOOKING = "booking"

# NFH HealthReferral lifecycleState values used in the reference flows.
LIFECYCLE_DRAFT = "DRAFT"
LIFECYCLE_ACTIVE = "ACTIVE"
LIFECYCLE_BOOKING_CONFIRMED = "BOOKING_CONFIRMED"
LIFECYCLE_CANCELLED = "CANCELLED"
LIFECYCLE_FULFILLED = "FULFILLED"

# HealthParticipant participantRole values.
PARTICIPANT_ROLE_PATIENT = "PATIENT"
