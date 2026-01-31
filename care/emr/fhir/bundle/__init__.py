"""
FHIR Bundle Processing Module

This module provides functionality to process FHIR bundles and create
corresponding resources in the care system. It is designed to be extensible
and follows the project's conventions for resource handling.

The bundle processor supports:
- Condition
- Observation
- MedicationRequest
- AllergyIntolerance
- ServiceRequest

Additional resource types can be added by implementing the FHIRResourceProcessor
base class and registering it with the processor registry.

Usage:
    from care.emr.fhir.bundle import FHIRBundleProcessor, FHIRResourceRegistry

    # Process a bundle
    processor = FHIRBundleProcessor(encounter_id=encounter_uuid, user=user)
    result = processor.process_bundle(bundle_data)

    # Check supported types
    types = FHIRResourceRegistry.get_supported_types()

Extensibility:
    To add support for a new FHIR resource type:

    1. Create a new processor in care/emr/fhir/bundle/processors/
    2. Inherit from FHIRResourceProcessor
    3. Implement the map_fhir_to_spec method
    4. Use the @register_processor decorator

    Example:
        from care.emr.fhir.bundle.base import FHIRResourceProcessor
        from care.emr.fhir.bundle.registry import register_processor

        @register_processor
        class MyResourceProcessor(FHIRResourceProcessor):
            resource_type = "MyResource"
            pydantic_spec = MyResourceSpec

            def map_fhir_to_spec(self, fhir_resource, encounter_id):
                return {...}
"""

from care.emr.fhir.bundle.processor import FHIRBundleProcessor
from care.emr.fhir.bundle.registry import FHIRResourceRegistry

__all__ = ["FHIRBundleProcessor", "FHIRResourceRegistry"]
