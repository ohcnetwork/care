"""
FHIR Resource Processors.

This module contains individual processors for each supported FHIR resource type.
All processors are automatically registered with the FHIRResourceRegistry when
this module is imported.
"""

# Import all processors to register them with the registry
from care.emr.fhir.bundle.processors.allergy_intolerance import (
    AllergyIntoleranceProcessor,
)
from care.emr.fhir.bundle.processors.condition import ConditionProcessor
from care.emr.fhir.bundle.processors.document_reference import (
    DocumentReferenceProcessor,
)
from care.emr.fhir.bundle.processors.medication_request import (
    MedicationRequestProcessor,
)
from care.emr.fhir.bundle.processors.medication_statement import (
    MedicationStatementProcessor,
)
from care.emr.fhir.bundle.processors.observation import ObservationProcessor
from care.emr.fhir.bundle.processors.service_request import ServiceRequestProcessor

__all__ = [
    "ConditionProcessor",
    "ObservationProcessor",
    "MedicationRequestProcessor",
    "MedicationStatementProcessor",
    "AllergyIntoleranceProcessor",
    "ServiceRequestProcessor",
    "DocumentReferenceProcessor",
]
