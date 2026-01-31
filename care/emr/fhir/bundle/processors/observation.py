"""
FHIR Observation Resource Processor.

Maps FHIR Observation resources to care Observation specs.
"""

import logging
from typing import Any

from django.contrib.auth import get_user_model
from pydantic import UUID4

from care.emr.fhir.bundle.base import FHIRResourceProcessor
from care.emr.fhir.bundle.registry import register_processor
from care.emr.models import Encounter
from care.emr.models.observation import Observation
from care.emr.resources.observation.spec import ObservationSpec, ObservationStatus
from care.emr.resources.questionnaire.spec import QuestionType

User = get_user_model()
logger = logging.getLogger(__name__)


@register_processor
class ObservationProcessor(FHIRResourceProcessor):
    """
    Processor for FHIR Observation resources.

    Maps FHIR Observation to care Observation model.

    FHIR Observation Reference:
    https://www.hl7.org/fhir/observation.html
    """

    resource_type = "Observation"
    pydantic_spec = ObservationSpec

    # Mapping from FHIR status to care enum
    STATUS_MAP = {
        "final": ObservationStatus.final,
        "amended": ObservationStatus.amended,
        "entered-in-error": ObservationStatus.entered_in_error,
    }

    def map_fhir_to_spec(
        self, fhir_resource: dict[str, Any], encounter_id: UUID4
    ) -> dict[str, Any]:
        """
        Map FHIR Observation to care ObservationSpec format.

        Args:
            fhir_resource: The FHIR Observation resource
            encounter_id: The encounter UUID

        Returns:
            Dictionary for ObservationSpec validation
        """
        spec_data = {
            "encounter": encounter_id,
        }

        # Map status (required)
        status = fhir_resource.get("status", "final")
        spec_data["status"] = self.STATUS_MAP.get(status, ObservationStatus.final)

        # Map category
        categories = fhir_resource.get("category", [])
        if categories:
            spec_data["category"] = self.map_codeable_concept_to_coding(categories[0])

        # Map code (main_code)
        code = fhir_resource.get("code")
        if code:
            spec_data["main_code"] = self.map_codeable_concept_to_coding(code)

        # Map effective datetime (required)
        if fhir_resource.get("effectiveDateTime"):
            spec_data["effective_datetime"] = fhir_resource.get("effectiveDateTime")
        elif fhir_resource.get("effectivePeriod"):
            period = fhir_resource.get("effectivePeriod", {})
            spec_data["effective_datetime"] = period.get("start")
        else:
            # Use current time as fallback
            from django.utils import timezone
            spec_data["effective_datetime"] = timezone.now().isoformat()

        # Map value[x] - determine type and value
        value_type, value = self._map_value(fhir_resource)
        spec_data["value_type"] = value_type
        spec_data["value"] = value

        # Map body site
        if fhir_resource.get("bodySite"):
            spec_data["body_site"] = self.map_codeable_concept_to_coding(
                fhir_resource.get("bodySite")
            )

        # Map method
        if fhir_resource.get("method"):
            spec_data["method"] = self.map_codeable_concept_to_coding(
                fhir_resource.get("method")
            )

        # Map interpretation
        interpretations = fhir_resource.get("interpretation", [])
        if interpretations:
            spec_data["interpretation"] = self.map_codeable_concept_to_coding(
                interpretations[0]
            ) or {}

        # Map reference range
        reference_ranges = fhir_resource.get("referenceRange", [])
        if reference_ranges:
            spec_data["reference_range"] = [
                self._map_reference_range(rr) for rr in reference_ranges
            ]

        # Map note
        notes = fhir_resource.get("note", [])
        if notes and notes[0].get("text"):
            spec_data["note"] = notes[0].get("text")

        # Map components
        components = fhir_resource.get("component", [])
        if components:
            spec_data["component"] = [
                self._map_component(comp) for comp in components
            ]

        return spec_data

    def _map_value(
        self, fhir_resource: dict[str, Any]
    ) -> tuple[QuestionType, Any]:
        """
        Map FHIR value[x] to care value type and value.

        Note: QuestionnaireSubmitResultValue expects:
        - value: str | None (must be string)
        - unit: Coding | None (for quantities)
        - coding: Coding | None (for coded values)

        Args:
            fhir_resource: The FHIR Observation resource

        Returns:
            Tuple of (value_type, value)
        """
        # Quantity value
        if fhir_resource.get("valueQuantity"):
            quantity = fhir_resource.get("valueQuantity", {})
            value = quantity.get("value")
            return QuestionType.decimal, {
                "value": str(value) if value is not None else None,
                "unit": {
                    "code": quantity.get("code") or quantity.get("unit"),
                    "display": quantity.get("unit"),
                    "system": quantity.get("system"),
                },
            }

        # CodeableConcept value
        if fhir_resource.get("valueCodeableConcept"):
            coding = self.map_codeable_concept_to_coding(
                fhir_resource.get("valueCodeableConcept")
            )
            return QuestionType.choice, {"coding": coding}

        # String value
        if fhir_resource.get("valueString"):
            return QuestionType.string, {"value": str(fhir_resource.get("valueString"))}

        # Boolean value
        if fhir_resource.get("valueBoolean") is not None:
            return QuestionType.boolean, {"value": str(fhir_resource.get("valueBoolean")).lower()}

        # Integer value
        if fhir_resource.get("valueInteger") is not None:
            return QuestionType.integer, {"value": str(fhir_resource.get("valueInteger"))}

        # DateTime value
        if fhir_resource.get("valueDateTime"):
            return QuestionType.dateTime, {"value": str(fhir_resource.get("valueDateTime"))}

        # Time value
        if fhir_resource.get("valueTime"):
            return QuestionType.time, {"value": str(fhir_resource.get("valueTime"))}

        # Range value
        if fhir_resource.get("valueRange"):
            range_val = fhir_resource.get("valueRange", {})
            low_val = range_val.get("low", {}).get("value")
            high_val = range_val.get("high", {}).get("value")
            # For range, use the midpoint as the value
            if low_val is not None and high_val is not None:
                midpoint = (float(low_val) + float(high_val)) / 2
                return QuestionType.decimal, {"value": str(midpoint)}
            elif low_val is not None:
                return QuestionType.decimal, {"value": str(low_val)}
            elif high_val is not None:
                return QuestionType.decimal, {"value": str(high_val)}

        # Ratio value
        if fhir_resource.get("valueRatio"):
            ratio = fhir_resource.get("valueRatio", {})
            numerator = ratio.get("numerator", {}).get("value")
            denominator = ratio.get("denominator", {}).get("value")
            if numerator and denominator:
                result = float(numerator) / float(denominator)
                return QuestionType.decimal, {"value": str(result)}

        # Default to string with empty value
        return QuestionType.string, {"value": ""}

    def _map_reference_range(self, reference_range: dict[str, Any]) -> dict[str, Any]:
        """
        Map FHIR referenceRange to care ReferenceRange format.

        Args:
            reference_range: FHIR reference range

        Returns:
            Care reference range dictionary
        """
        result = {}

        if reference_range.get("low"):
            low = reference_range.get("low", {})
            result["min"] = low.get("value")
            result["unit"] = low.get("unit")

        if reference_range.get("high"):
            high = reference_range.get("high", {})
            result["max"] = high.get("value")
            result["unit"] = result.get("unit") or high.get("unit")

        if reference_range.get("text"):
            result["value"] = reference_range.get("text")

        # Map interpretation from type
        type_coding = reference_range.get("type", {})
        if type_coding:
            codings = type_coding.get("coding", [])
            if codings:
                result["interpretation"] = codings[0].get("code", "normal")
            else:
                result["interpretation"] = "normal"
        else:
            result["interpretation"] = "normal"

        return result

    def _map_component(self, component: dict[str, Any]) -> dict[str, Any]:
        """
        Map FHIR component to care Component format.

        Args:
            component: FHIR component

        Returns:
            Care component dictionary
        """
        result = {}

        # Map code
        if component.get("code"):
            result["code"] = self.map_codeable_concept_to_coding(component.get("code"))

        # Map value
        _, value = self._map_value(component)
        result["value"] = value

        # Map interpretation
        interpretations = component.get("interpretation", [])
        if interpretations:
            result["interpretation"] = (
                self.map_codeable_concept_to_coding(interpretations[0]) or {}
            )
        else:
            result["interpretation"] = {}

        # Map reference range
        reference_ranges = component.get("referenceRange", [])
        if reference_ranges:
            result["reference_range"] = [
                self._map_reference_range(rr) for rr in reference_ranges
            ]
        else:
            result["reference_range"] = []

        result["note"] = ""

        return result

    def process(self, fhir_resource: dict[str, Any]) -> dict[str, Any]:
        """
        Process a FHIR Observation and create the care Observation.

        Overridden to handle:
        1. Special case where ObservationSpec requires user IDs directly
        2. Properly generate external_id
        3. Bypass ValueSetBoundCoding validation for body_site and method fields
           that may contain codes not in the system's valuesets

        Args:
            fhir_resource: The FHIR Observation resource

        Returns:
            Processing result dictionary
        """
        import uuid

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

            # Generate a new UUID for the observation (ObservationSpec uses self.id for external_id)
            spec_data["id"] = uuid.uuid4()

            # Add required user IDs for ObservationSpec
            spec_data["data_entered_by_id"] = self.user.id
            spec_data["created_by_id"] = self.user.id
            spec_data["updated_by_id"] = self.user.id

            # Extract fields that may fail ValueSetBoundCoding validation
            # These will be set directly on the model instance
            body_site = spec_data.pop("body_site", None)
            method = spec_data.pop("method", None)

            # Validate the spec (without body_site and method)
            pydantic_instance = self.pydantic_spec.model_validate(spec_data)

            # Deserialize to model instance
            model_instance = pydantic_instance.de_serialize()

            # Set encounter and patient
            model_instance.encounter = self.encounter
            model_instance.patient = self.encounter.patient

            # Set subject_id based on subject_type (default is encounter)
            if model_instance.subject_type == "patient":
                model_instance.subject_id = self.encounter.patient.external_id
            else:
                # Default to encounter
                model_instance.subject_id = self.encounter.external_id

            # Set body_site and method directly (bypassing ValueSetBoundCoding validation)
            if body_site:
                model_instance.body_site = body_site
            if method:
                model_instance.method = method

            # Save the instance
            model_instance.save()

            result["success"] = True
            result["care_id"] = str(model_instance.external_id)

        except Exception as e:
            logger.exception(f"Error processing FHIR Observation: {e}")
            result["errors"] = [str(e)]

        return result

    def validate_fhir_resource(self, fhir_resource: dict[str, Any]) -> list[str]:
        """
        Validate the FHIR Observation resource.

        Args:
            fhir_resource: The FHIR Observation resource

        Returns:
            List of validation errors
        """
        errors = super().validate_fhir_resource(fhir_resource)

        # Code is required
        if not fhir_resource.get("code"):
            errors.append("Observation.code is required")

        # Status is required
        if not fhir_resource.get("status"):
            errors.append("Observation.status is required")

        return errors
