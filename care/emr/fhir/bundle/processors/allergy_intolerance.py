"""
FHIR AllergyIntolerance Resource Processor.

Maps FHIR AllergyIntolerance resources to care AllergyIntolerance specs.
"""

import logging
from typing import Any

from dateutil.parser import parse as parse_datetime
from pydantic import UUID4

from care.emr.fhir.bundle.base import FHIRResourceProcessor
from care.emr.fhir.bundle.registry import register_processor
from care.emr.models.allergy_intolerance import AllergyIntolerance
from care.emr.resources.allergy_intolerance.spec import (
    AllergyIntoleranceTypeOptions,
    AllergyIntoleranceWriteSpec,
    CategoryChoices,
    ClinicalStatusChoices,
    CriticalityChoices,
    VerificationStatusChoices,
)

logger = logging.getLogger(__name__)


@register_processor
class AllergyIntoleranceProcessor(FHIRResourceProcessor):
    """
    Processor for FHIR AllergyIntolerance resources.

    Maps FHIR AllergyIntolerance to care AllergyIntolerance model.

    FHIR AllergyIntolerance Reference:
    https://www.hl7.org/fhir/allergyintolerance.html
    """

    resource_type = "AllergyIntolerance"
    pydantic_spec = AllergyIntoleranceWriteSpec

    # Mapping from FHIR clinical status to care enum
    CLINICAL_STATUS_MAP = {
        "active": ClinicalStatusChoices.active,
        "inactive": ClinicalStatusChoices.inactive,
        "resolved": ClinicalStatusChoices.resolved,
    }

    # Mapping from FHIR verification status to care enum
    VERIFICATION_STATUS_MAP = {
        "unconfirmed": VerificationStatusChoices.unconfirmed,
        "presumed": VerificationStatusChoices.presumed,
        "confirmed": VerificationStatusChoices.confirmed,
        "refuted": VerificationStatusChoices.refuted,
        "entered-in-error": VerificationStatusChoices.entered_in_error,
    }

    # Mapping from FHIR category to care enum
    CATEGORY_MAP = {
        "food": CategoryChoices.food,
        "medication": CategoryChoices.medication,
        "environment": CategoryChoices.environment,
        "biologic": CategoryChoices.biologic,
    }

    # Mapping from FHIR criticality to care enum
    CRITICALITY_MAP = {
        "low": CriticalityChoices.low,
        "high": CriticalityChoices.high,
        "unable-to-assess": CriticalityChoices.unable_to_assess,
    }

    # Mapping from FHIR type to care enum
    TYPE_MAP = {
        "allergy": AllergyIntoleranceTypeOptions.allergy,
        "intolerance": AllergyIntoleranceTypeOptions.intolerance,
    }

    def map_fhir_to_spec(
        self, fhir_resource: dict[str, Any], encounter_id: UUID4
    ) -> dict[str, Any]:
        """
        Map FHIR AllergyIntolerance to care AllergyIntoleranceWriteSpec format.

        Args:
            fhir_resource: The FHIR AllergyIntolerance resource
            encounter_id: The encounter UUID

        Returns:
            Dictionary for AllergyIntoleranceWriteSpec validation
        """
        spec_data = {
            "encounter": encounter_id,
        }

        # Map clinical status (required)
        clinical_status = self._extract_coding_code(
            fhir_resource.get("clinicalStatus")
        )
        if clinical_status:
            spec_data["clinical_status"] = self.CLINICAL_STATUS_MAP.get(
                clinical_status, ClinicalStatusChoices.active
            )
        else:
            spec_data["clinical_status"] = ClinicalStatusChoices.active

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
            spec_data["category"] = self.CATEGORY_MAP.get(
                categories[0], CategoryChoices.medication
            )
        else:
            spec_data["category"] = CategoryChoices.medication

        # Map criticality (required)
        criticality = fhir_resource.get("criticality")
        if criticality:
            spec_data["criticality"] = self.CRITICALITY_MAP.get(
                criticality, CriticalityChoices.low
            )
        else:
            spec_data["criticality"] = CriticalityChoices.low

        # Map type (allergy or intolerance)
        allergy_type = fhir_resource.get("type")
        if allergy_type:
            spec_data["allergy_intolerance_type"] = self.TYPE_MAP.get(
                allergy_type, AllergyIntoleranceTypeOptions.allergy
            )
        else:
            spec_data["allergy_intolerance_type"] = AllergyIntoleranceTypeOptions.allergy

        # Map code (required)
        code = fhir_resource.get("code")
        if code:
            spec_data["code"] = self.map_codeable_concept_to_coding(code)

        # Map onset
        onset = self._map_onset(fhir_resource)
        if onset:
            spec_data["onset"] = onset

        # Map last occurrence
        if fhir_resource.get("lastOccurrence"):
            spec_data["last_occurrence"] = fhir_resource.get("lastOccurrence")

        # Map recorded date
        if fhir_resource.get("recordedDate"):
            spec_data["recorded_date"] = fhir_resource.get("recordedDate")

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
        Map FHIR onset[x] to care AllergyIntoleranceOnSetSpec.

        Args:
            fhir_resource: The FHIR AllergyIntolerance resource

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

        # Note is part of the onset spec
        notes = fhir_resource.get("note", [])
        if notes and notes[0].get("text"):
            onset["note"] = notes[0].get("text")
        else:
            onset["note"] = ""

        return onset if any(k != "note" and v for k, v in onset.items()) else {"note": ""}

    def validate_fhir_resource(self, fhir_resource: dict[str, Any]) -> list[str]:
        """
        Validate the FHIR AllergyIntolerance resource.

        Note: Code validation is handled separately in process() to allow
        skipping instead of failing.

        Args:
            fhir_resource: The FHIR AllergyIntolerance resource

        Returns:
            List of validation errors
        """
        errors = super().validate_fhir_resource(fhir_resource)
        # Note: Code validation moved to process() to allow skipping
        return errors

    def _has_valid_code(self, fhir_resource: dict[str, Any]) -> bool:
        """
        Check if the FHIR resource has a valid code field with actual coding data.

        Args:
            fhir_resource: The FHIR AllergyIntolerance resource

        Returns:
            True if code is present with valid coding data, False otherwise
        """
        code = fhir_resource.get("code")
        if not code:
            return False

        # Check for valid coding entries (must have at least a code value)
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
        Process a FHIR AllergyIntolerance and create the care AllergyIntolerance.

        Overridden to bypass ValueSetBoundCoding validation for codes
        that may not exist in the care system's valuesets when importing from
        external FHIR systems.

        AllergyIntolerance without a valid code are skipped (not failed).

        Args:
            fhir_resource: The FHIR AllergyIntolerance resource

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
                f"Skipping AllergyIntolerance without valid code: {fhir_resource.get('id')}"
            )
            return {
                "success": True,
                "resource_type": self.resource_type,
                "fhir_id": fhir_resource.get("id"),
                "skipped": True,
                "message": "AllergyIntolerance without valid code is not allowed and was skipped",
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
            model_instance = AllergyIntolerance()

            # Set basic fields
            model_instance.clinical_status = spec_data.get(
                "clinical_status", ClinicalStatusChoices.active
            ).value
            model_instance.verification_status = spec_data.get(
                "verification_status", VerificationStatusChoices.unconfirmed
            ).value
            model_instance.category = spec_data.get(
                "category", CategoryChoices.medication
            ).value
            model_instance.criticality = spec_data.get(
                "criticality", CriticalityChoices.low
            ).value
            model_instance.allergy_intolerance_type = spec_data.get(
                "allergy_intolerance_type", AllergyIntoleranceTypeOptions.allergy
            ).value

            # Set code directly (bypassing ValueSetBoundCoding validation)
            model_instance.code = spec_data.get("code")

            # Set onset
            model_instance.onset = spec_data.get("onset", {})

            # Set last_occurrence
            last_occurrence = spec_data.get("last_occurrence")
            if last_occurrence:
                if isinstance(last_occurrence, str):
                    model_instance.last_occurrence = parse_datetime(last_occurrence)
                else:
                    model_instance.last_occurrence = last_occurrence

            # Set recorded_date
            recorded_date = spec_data.get("recorded_date")
            if recorded_date:
                if isinstance(recorded_date, str):
                    model_instance.recorded_date = parse_datetime(recorded_date)
                else:
                    model_instance.recorded_date = recorded_date

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
            logger.exception(f"Error processing FHIR AllergyIntolerance: {e}")
            result["errors"] = [str(e)]

        return result
