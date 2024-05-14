from django.db import models


class Status(models.TextChoices):
    REQUESTED = "REQUESTED"
    GRANTED = "GRANTED"
    DENIED = "DENIED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class Purpose(models.TextChoices):
    CARE_MANAGEMENT = "CAREMGT"
    BREAK_THE_GLASS = "BTG"
    PUBLIC_HEALTH = "PUBHLTH"
    HEALTHCARE_PAYMENT = "HPAYMT"
    DISEASE_SPECIFIC_HEALTHCARE_RESEARCH = "DSRCH"
    SELF_REQUESTED = "PATRQT"


class HealthInformationTypes(models.TextChoices):
    PRESCRIPTION = "Prescription"
    DIAGNOSTIC_REPORT = "DiagnosticReport"
    OP_CONSULTATION = "OPConsultation"
    DISCHARGE_SUMMARY = "DischargeSummary"
    IMMUNIZATION_RECORD = "ImmunizationRecord"
    RECORD_ARTIFACT = "HealthDocumentRecord"
    WELLNESS_RECORD = "WellnessRecord"


class AccessMode(models.TextChoices):
    VIEW = "VIEW"
    STORE = "STORE"
    QUERY = "QUERY"
    STREAM = "STREAM"


class FrequencyUnit(models.TextChoices):
    HOUR = "HOUR"
    DAY = "DAY"
    WEEK = "WEEK"
    MONTH = "MONTH"
    YEAR = "YEAR"
