"""
Base classes for FHIR resource processing.

This module provides the abstract base class for implementing FHIR resource
processors. Each processor is responsible for mapping FHIR resource data
to the corresponding care system resource specs.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, ClassVar

from django.contrib.auth import get_user_model
from pydantic import UUID4

from care.emr.models import Encounter
from care.emr.resources.base import EMRResource

User = get_user_model()
logger = logging.getLogger(__name__)


class FHIRResourceProcessor(ABC):
    """
    Abstract base class for FHIR resource processors.

    Each processor is responsible for:
    1. Mapping FHIR resource data to care system resource specs
    2. Validating the mapped data
    3. Creating the resource in the database

    To implement a new processor:
    1. Subclass FHIRResourceProcessor
    2. Set the `resource_type` class attribute to the FHIR resource type
    3. Set the `pydantic_spec` class attribute to the create spec
    4. Implement the `map_fhir_to_spec` method

    Example:
        class ConditionProcessor(FHIRResourceProcessor):
            resource_type = "Condition"
            pydantic_spec = ConditionSpec

            def map_fhir_to_spec(self, fhir_resource, encounter_id):
                return {
                    "encounter": encounter_id,
                    "code": self.map_codeable_concept(fhir_resource.get("code")),
                    ...
                }
    """

    # The FHIR resource type this processor handles (e.g., "Condition", "Observation")
    resource_type: ClassVar[str] = None

    # The Pydantic spec class for creating resources
    pydantic_spec: ClassVar[type[EMRResource]] = None

    def __init__(self, encounter: Encounter, user: User):
        """
        Initialize the processor with encounter context.

        Args:
            encounter: The encounter context for resource creation
            user: The user creating the resources
        """
        self.encounter = encounter
        self.user = user

    @abstractmethod
    def map_fhir_to_spec(
        self, fhir_resource: dict[str, Any], encounter_id: UUID4
    ) -> dict[str, Any]:
        """
        Map FHIR resource data to care system spec format.

        This method must be implemented by subclasses to handle the specific
        mapping logic for each resource type.

        Args:
            fhir_resource: The FHIR resource data dictionary
            encounter_id: The encounter UUID to associate with the resource

        Returns:
            A dictionary that can be validated against the pydantic_spec
        """
        pass

    def validate_fhir_resource(self, fhir_resource: dict[str, Any]) -> list[str]:
        """
        Validate the FHIR resource data before processing.

        Override this method to add custom validation logic.

        Args:
            fhir_resource: The FHIR resource data dictionary

        Returns:
            A list of validation error messages (empty if valid)
        """
        errors = []
        if not fhir_resource.get("resourceType"):
            errors.append("Missing resourceType in FHIR resource")
        elif fhir_resource.get("resourceType") != self.resource_type:
            errors.append(
                f"Expected resourceType '{self.resource_type}', "
                f"got '{fhir_resource.get('resourceType')}'"
            )
        return errors

    def process(self, fhir_resource: dict[str, Any]) -> dict[str, Any]:
        """
        Process a FHIR resource and create the corresponding care resource.

        Args:
            fhir_resource: The FHIR resource data dictionary

        Returns:
            A dictionary containing the processing result with:
            - success: bool
            - resource_type: str
            - fhir_id: str (if provided in FHIR resource)
            - care_id: UUID (if successful)
            - errors: list[str] (if failed)
        """
        result = {
            "success": False,
            "resource_type": self.resource_type,
            "fhir_id": fhir_resource.get("id"),
        }

        # Validate FHIR resource
        validation_errors = self.validate_fhir_resource(fhir_resource)
        if validation_errors:
            result["errors"] = validation_errors
            return result

        try:
            # Map FHIR to spec format
            spec_data = self.map_fhir_to_spec(
                fhir_resource, self.encounter.external_id
            )

            # Validate and create the resource
            pydantic_instance = self.pydantic_spec.model_validate(spec_data)

            # Deserialize to model instance
            model_instance = pydantic_instance.de_serialize()

            # Set audit fields
            model_instance.created_by = self.user
            model_instance.updated_by = self.user

            # Save the instance
            model_instance.save()

            result["success"] = True
            result["care_id"] = str(model_instance.external_id)

        except Exception as e:
            logger.exception(
                f"Error processing FHIR {self.resource_type}: {e}"
            )
            result["errors"] = [str(e)]

        return result

    # Helper methods for common FHIR to care mappings

    @staticmethod
    def map_codeable_concept(codeable_concept: dict | None) -> dict | None:
        """
        Map a FHIR CodeableConcept to care Coding format.

        Args:
            codeable_concept: FHIR CodeableConcept dictionary

        Returns:
            Care Coding dictionary or None
        """
        if not codeable_concept:
            return None

        # Use the first coding if available
        codings = codeable_concept.get("coding", [])
        if codings:
            first_coding = codings[0]
            # Ensure code is a string (FHIR allows numeric codes in JSON)
            code = first_coding.get("code")
            return {
                "code": str(code) if code is not None else None,
                "display": first_coding.get("display"),
                "system": first_coding.get("system"),
            }

        # Fallback to text
        if codeable_concept.get("text"):
            return {
                "display": codeable_concept.get("text"),
            }

        return None

    @staticmethod
    def map_codeable_concept_to_coding(codeable_concept: dict | None) -> dict | None:
        """
        Map a FHIR CodeableConcept to care Coding format for ValueSetBoundCoding.

        Args:
            codeable_concept: FHIR CodeableConcept dictionary

        Returns:
            Care Coding dictionary suitable for ValueSetBoundCoding
        """
        if not codeable_concept:
            return None

        codings = codeable_concept.get("coding", [])
        if codings:
            first_coding = codings[0]
            # Ensure code is a string (FHIR allows numeric codes in JSON)
            code = first_coding.get("code")
            return {
                "code": str(code) if code is not None else None,
                "display": first_coding.get("display"),
                "system": first_coding.get("system"),
            }
        return None

    @staticmethod
    def map_period(period: dict | None) -> dict | None:
        """
        Map a FHIR Period to care PeriodSpec format.

        Args:
            period: FHIR Period dictionary

        Returns:
            Care PeriodSpec dictionary or None
        """
        if not period:
            return None

        return {
            "start": period.get("start"),
            "end": period.get("end"),
        }

    @staticmethod
    def map_quantity(quantity: dict | None) -> dict | None:
        """
        Map a FHIR Quantity to care format.

        Args:
            quantity: FHIR Quantity dictionary

        Returns:
            Care quantity dictionary or None
        """
        if not quantity:
            return None

        return {
            "value": quantity.get("value"),
            "unit": quantity.get("unit") or quantity.get("code"),
        }

    @staticmethod
    def extract_reference_id(reference: str | None) -> str | None:
        """
        Extract the ID from a FHIR reference string.

        Args:
            reference: FHIR reference string (e.g., "Patient/123")

        Returns:
            The extracted ID or None
        """
        if not reference:
            return None

        if "/" in reference:
            return reference.split("/")[-1]
        return reference
