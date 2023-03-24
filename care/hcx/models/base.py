from enum import Enum


# http://hl7.org/fhir/fm-status
class StatusEnum(Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    DRAFT = "draft"
    ENTERED_IN_ERROR = "entered-in-error"


STATUS_CHOICES = [(item.value, item.name) for item in StatusEnum]


# http://terminology.hl7.org/CodeSystem/processpriority
class PriorityEnum(Enum):
    IMMEDIATE = "stat"
    NORMAL = "normal"
    DEFERRED = "deferred"


PRIORITY_CHOICES = [(item.value, item.name) for item in PriorityEnum]


# http://hl7.org/fhir/eligibilityrequest-purpose
class PurposeEnum(Enum):
    AUTH_REQUIREMENTS = "auth-requirements"
    BENEFITS = "benefits"
    DISCOVERY = "discovery"
    VALIDATION = "validation"


PURPOSE_CHOICES = [(item.value, item.name) for item in PurposeEnum]


# http://hl7.org/fhir/remittance-outcome
class OutcomeEnum(Enum):
    QUEUED = "queued"
    COMPLETE = "complete"
    ERROR = "error"
    PARTIAL_PROCESSING = "partial"


OUTCOME_CHOICES = [(item.value, item.name) for item in OutcomeEnum]


# http://hl7.org/fhir/claim-use
class UseEnum(Enum):
    CLAIM = "claim"
    PRE_AUTHORIZATION = "preauthorization"
    PRE_DETERMINATION = "predetermination"


USE_CHOICES = [(item.value, item.name) for item in UseEnum]


# http://hl7.org/fhir/claim-use
class ClaimTypeEnum(Enum):
    INSTITUTIONAL = "institutional"
    ORAL = "oral"
    PHARMACY = "pharmacy"
    PROFESSIONAL = "professional"
    VISION = "vision"


CLAIM_TYPE_CHOICES = [(item.value, item.name) for item in ClaimTypeEnum]
