from django.db import models


# http://hl7.org/fhir/fm-status
class StatusEnum(models.TextChoices):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    DRAFT = "draft"
    ENTERED_IN_ERROR = "entered-in-error"


# http://terminology.hl7.org/CodeSystem/processpriority
class PriorityEnum(models.TextChoices):
    IMMEDIATE = "stat"
    NORMAL = "normal"
    DEFERRED = "deferred"


# http://hl7.org/fhir/eligibilityrequest-purpose
class PurposeEnum(models.TextChoices):
    AUTH_REQUIREMENTS = "auth-requirements"
    BENEFITS = "benefits"
    DISCOVERY = "discovery"
    VALIDATION = "validation"


# http://hl7.org/fhir/remittance-outcome
class OutcomeEnum(models.TextChoices):
    QUEUED = "queued"
    COMPLETE = "complete"
    ERROR = "error"
    PARTIAL_PROCESSING = "partial"


# http://hl7.org/fhir/claim-use
class UseEnum(models.TextChoices):
    CLAIM = "claim"
    PRE_AUTHORIZATION = "preauthorization"
    PRE_DETERMINATION = "predetermination"


# http://hl7.org/fhir/claim-use
class ClaimTypeEnum(models.TextChoices):
    INSTITUTIONAL = "institutional"
    ORAL = "oral"
    PHARMACY = "pharmacy"
    PROFESSIONAL = "professional"
    VISION = "vision"
