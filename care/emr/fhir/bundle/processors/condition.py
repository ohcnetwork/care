"""
FHIR Condition Resource Processor.

Maps FHIR Condition resources to care Condition specs.
"""

import logging
from typing import Any

from pydantic import UUID4

from care.emr.fhir.bundle.base import FHIRResourceProcessor
from care.emr.fhir.bundle.registry import register_processor
from care.emr.models.condition import Condition
from care.emr.resources.condition.spec import (
    CategoryChoices,
    ClinicalStatusChoices,
    ConditionSpec,
    SeverityChoices,
    VerificationStatusChoices,
)

logger = logging.getLogger(__name__)


@register_processor
class ConditionProcessor(FHIRResourceProcessor):
    """
    Processor for FHIR Condition resources.

    Maps FHIR Condition to care Condition model.

    FHIR Condition Reference:
    https://www.hl7.org/fhir/condition.html
    """

    resource_type = "Condition"
    pydantic_spec = ConditionSpec

    # Mapping from FHIR clinical status to care enum
    CLINICAL_STATUS_MAP = {
        "active": ClinicalStatusChoices.active,
        "recurrence": ClinicalStatusChoices.recurrence,
        "relapse": ClinicalStatusChoices.relapse,
        "inactive": ClinicalStatusChoices.inactive,
        "remission": ClinicalStatusChoices.remission,
        "resolved": ClinicalStatusChoices.resolved,
    }

    # Mapping from FHIR verification status to care enum
    VERIFICATION_STATUS_MAP = {
        "unconfirmed": VerificationStatusChoices.unconfirmed,
        "provisional": VerificationStatusChoices.provisional,
        "differential": VerificationStatusChoices.differential,
        "confirmed": VerificationStatusChoices.confirmed,
        "refuted": VerificationStatusChoices.refuted,
        "entered-in-error": VerificationStatusChoices.entered_in_error,
    }

    # Mapping from FHIR category to care enum
    CATEGORY_MAP = {
        "problem-list-item": CategoryChoices.problem_list_item,
        "encounter-diagnosis": CategoryChoices.encounter_diagnosis,
    }

    # Mapping from FHIR severity to care enum
    SEVERITY_MAP = {
        "mild": SeverityChoices.mild,
        "moderate": SeverityChoices.moderate,
        "severe": SeverityChoices.severe,
    }

    def map_fhir_to_spec(
        self, fhir_resource: dict[str, Any], encounter_id: UUID4
    ) -> dict[str, Any]:
        """
        Map FHIR Condition to care ConditionSpec format.

        Args:
            fhir_resource: The FHIR Condition resource
            encounter_id: The encounter UUID

        Returns:
            Dictionary for ConditionSpec validation
        """
        spec_data = {
            "encounter": encounter_id,
        }

        # Map clinical status
        clinical_status = self._extract_coding_code(
            fhir_resource.get("clinicalStatus")
        )
        if clinical_status:
            spec_data["clinical_status"] = self.CLINICAL_STATUS_MAP.get(
                clinical_status, ClinicalStatusChoices.unknown
            )

        # Map verification status (required)
        verification_status = self._extract_coding_code(
            fhir_resource.get("verificationStatus")
        )
        if verification_status:
            spec_data["verification_status"] = self.VERIFICATION_STATUS_MAP.get(
                verification_status, VerificationStatusChoices.unconfirmed
            )
        else:
            spec_data["verification_status"] = VerificationStatusChoices.unconfirmed

        # Map category (required)
        categories = fhir_resource.get("category", [])
        if categories:
            category_code = self._extract_coding_code(categories[0])
            spec_data["category"] = self.CATEGORY_MAP.get(
                category_code, CategoryChoices.encounter_diagnosis
            )
        else:
            spec_data["category"] = CategoryChoices.encounter_diagnosis

        # Map severity
        severity = self._extract_coding_code(fhir_resource.get("severity"))
        if severity:
            spec_data["severity"] = self.SEVERITY_MAP.get(severity)

        # Map code (required)
        code = fhir_resource.get("code")
        if code:
            spec_data["code"] = self.map_codeable_concept_to_coding(code)

        # Map onset
        onset = self._map_onset(fhir_resource)
        if onset:
            spec_data["onset"] = onset

        # Map abatement
        abatement = self._map_abatement(fhir_resource)
        if abatement:
            spec_data["abatement"] = abatement

        # Map note
        notes = fhir_resource.get("note", [])
        if notes and notes[0].get("text"):
            spec_data["note"] = notes[0].get("text")

        return spec_data

    def _extract_coding_code(self, codeable_concept: dict | None) -> str | None:
        """
        Extract the code from a CodeableConcept.

        Args:
            codeable_concept: FHIR CodeableConcept

        Returns:
            The code string or None
        """
        if not codeable_concept:
            return None

        codings = codeable_concept.get("coding", [])
        if codings:
            return codings[0].get("code")
        return None

    def _map_onset(self, fhir_resource: dict[str, Any]) -> dict | None:
        """
        Map FHIR onset[x] to care ConditionOnSetSpec.

        Args:
            fhir_resource: The FHIR Condition resource

        Returns:
            Onset dictionary or None
        """
        onset = {}

        if fhir_resource.get("onsetDateTime"):
            onset["onset_datetime"] = fhir_resource.get("onsetDateTime")
        elif fhir_resource.get("onsetAge"):
            age = fhir_resource.get("onsetAge", {})
            onset["onset_age"] = age.get("value")
        elif fhir_resource.get("onsetString"):
            onset["onset_string"] = fhir_resource.get("onsetString")

        return onset if onset else None

    def _map_abatement(self, fhir_resource: dict[str, Any]) -> dict | None:
        """
        Map FHIR abatement[x] to care ConditionAbatementSpec.

        Args:
            fhir_resource: The FHIR Condition resource

        Returns:
            Abatement dictionary or None
        """
        abatement = {}

        if fhir_resource.get("abatementDateTime"):
            abatement["abatement_datetime"] = fhir_resource.get("abatementDateTime")
        elif fhir_resource.get("abatementAge"):
            age = fhir_resource.get("abatementAge", {})
            abatement["abatement_age"] = age.get("value")
        elif fhir_resource.get("abatementString"):
            abatement["abatement_string"] = fhir_resource.get("abatementString")

        return abatement if abatement else None

    def validate_fhir_resource(self, fhir_resource: dict[str, Any]) -> list[str]:
        """
        Validate the FHIR Condition resource.

        Note: Code validation is handled separately in process() to allow
        skipping instead of failing.

        Args:
            fhir_resource: The FHIR Condition resource

        Returns:
            List of validation errors
        """
        errors = super().validate_fhir_resource(fhir_resource)
        # Note: Code validation moved to process() to allow skipping
        return errors

    def _has_valid_code(self, fhir_resource: dict[str, Any]) -> bool:
        """
        Check if the FHIR resource has a valid code field with actual coding data.

        Note: Text-only codes are not considered valid because the care system
        requires structured coding data (BoundCoding).

        Args:
            fhir_resource: The FHIR Condition resource

        Returns:
            True if code is present with valid coding data, False otherwise
        """
        code = fhir_resource.get("code")
        if not code:
            return False

        # Check for valid coding entries (must have at least a code value)
        # Text-only is not sufficient as care requires structured coding
        codings = code.get("coding", [])
        if not codings:
            return False

        # At least one coding must have a code value
        for coding in codings:
            if coding.get("code"):
                return True

        return False

    def process(self, fhir_resource: dict[str, Any]) -> dict[str, Any]:
        """
        Process a FHIR Condition and create the care Condition.

        Overridden to bypass ValueSetBoundCoding validation for condition codes
        that may not exist in the care system's valuesets when importing from
        external FHIR systems.

        Conditions without a code are skipped (not failed).

        Args:
            fhir_resource: The FHIR Condition resource

        Returns:
            Processing result dictionary
        """
        result = {
            "success": False,
            "resource_type": self.resource_type,
            "fhir_id": fhir_resource.get("id"),
        }

        # Check if code is present and valid - skip if not
        if not self._has_valid_code(fhir_resource):
            logger.info(
                f"Skipping Condition without valid code: {fhir_resource.get('id')}"
            )
            return {
                "success": True,
                "resource_type": self.resource_type,
                "fhir_id": fhir_resource.get("id"),
                "skipped": True,
                "message": "Condition without valid code is not allowed and was skipped",
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

            # Create the model instance directly to bypass ValueSetBoundCoding validation
            model_instance = Condition()

            # Set clinical status
            clinical_status = spec_data.get("clinical_status")
            if clinical_status:
                model_instance.clinical_status = (
                    clinical_status.value if hasattr(clinical_status, "value") else clinical_status
                )

            # Set verification status
            verification_status = spec_data.get("verification_status")
            if verification_status:
                model_instance.verification_status = (
                    verification_status.value if hasattr(verification_status, "value") else verification_status
                )

            # Set category
            category = spec_data.get("category")
            if category:
                model_instance.category = (
                    category.value if hasattr(category, "value") else category
                )

            # Set severity
            severity = spec_data.get("severity")
            if severity:
                model_instance.severity = (
                    severity.value if hasattr(severity, "value") else severity
                )

            # Set code directly (bypassing ValueSetBoundCoding validation)
            model_instance.code = spec_data.get("code", {})

            # Set body_site (default to empty dict)
            model_instance.body_site = {}

            # Set onset
            model_instance.onset = spec_data.get("onset", {})

            # Set abatement
            model_instance.abatement = spec_data.get("abatement", {})

            # Set note
            model_instance.note = spec_data.get("note")

            # Set encounter and patient
            model_instance.encounter = self.encounter
            model_instance.patient = self.encounter.patient

            # Set audit fields
            model_instance.created_by = self.user
            model_instance.updated_by = self.user

            # Save the instance
            model_instance.save()

            result["success"] = True
            result["care_id"] = str(model_instance.external_id)

        except Exception as e:
            logger.exception(f"Error processing FHIR Condition: {e}")
            result["errors"] = [str(e)]

        return result
