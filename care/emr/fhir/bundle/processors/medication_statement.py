"""
FHIR MedicationStatement Resource Processor.

Maps FHIR MedicationStatement resources to care MedicationStatement specs.
"""

import logging
from typing import Any

from dateutil.parser import parse as parse_datetime
from pydantic import UUID4

from care.emr.fhir.bundle.base import FHIRResourceProcessor
from care.emr.fhir.bundle.registry import register_processor
from care.emr.models.medication_statement import MedicationStatement
from care.emr.resources.medication.statement.spec import (
    MedicationStatementInformationSourceType,
    MedicationStatementSpec,
    MedicationStatementStatus,
)

logger = logging.getLogger(__name__)


@register_processor
class MedicationStatementProcessor(FHIRResourceProcessor):
    """
    Processor for FHIR MedicationStatement resources.

    Maps FHIR MedicationStatement to care MedicationStatement model.

    FHIR MedicationStatement Reference:
    https://www.hl7.org/fhir/medicationstatement.html
    """

    resource_type = "MedicationStatement"
    pydantic_spec = MedicationStatementSpec

    # Mapping from FHIR status to care enum
    STATUS_MAP = {
        "active": MedicationStatementStatus.active,
        "completed": MedicationStatementStatus.completed,
        "entered-in-error": MedicationStatementStatus.entered_in_error,
        "intended": MedicationStatementStatus.intended,
        "stopped": MedicationStatementStatus.stopped,
        "on-hold": MedicationStatementStatus.on_hold,
        "unknown": MedicationStatementStatus.unknown,
        "not-taken": MedicationStatementStatus.not_taken,
    }

    # Mapping from FHIR informationSource type to care enum
    INFORMATION_SOURCE_MAP = {
        "Patient": MedicationStatementInformationSourceType.patient,
        "Practitioner": MedicationStatementInformationSourceType.practitioner,
        "RelatedPerson": MedicationStatementInformationSourceType.related_person,
    }

    def map_fhir_to_spec(
        self, fhir_resource: dict[str, Any], encounter_id: UUID4
    ) -> dict[str, Any]:
        """
        Map FHIR MedicationStatement to care MedicationStatementSpec format.

        Args:
            fhir_resource: The FHIR MedicationStatement resource
            encounter_id: The encounter UUID

        Returns:
            Dictionary for MedicationStatementSpec validation
        """
        spec_data = {
            "encounter": encounter_id,
        }

        # Map status (required)
        status = fhir_resource.get("status", "active")
        spec_data["status"] = self.STATUS_MAP.get(
            status, MedicationStatementStatus.active
        )

        # Map medication (required)
        medication = None
        if fhir_resource.get("medicationCodeableConcept"):
            medication = self.map_codeable_concept_to_coding(
                fhir_resource.get("medicationCodeableConcept")
            )
        elif fhir_resource.get("medicationReference"):
            # For references, try to extract display name
            ref = fhir_resource.get("medicationReference", {})
            if ref.get("display"):
                medication = {
                    "display": ref.get("display"),
                    "code": ref.get("reference", "").split("/")[-1] if ref.get("reference") else None,
                }

        spec_data["medication"] = medication

        # Map effective period
        if fhir_resource.get("effectivePeriod"):
            period = fhir_resource.get("effectivePeriod", {})
            spec_data["effective_period"] = {
                "start": period.get("start"),
                "end": period.get("end"),
            }
        elif fhir_resource.get("effectiveDateTime"):
            spec_data["effective_period"] = {
                "start": fhir_resource.get("effectiveDateTime"),
            }

        # Map information source
        if fhir_resource.get("informationSource"):
            source = fhir_resource.get("informationSource", {})
            # Try to determine type from reference
            ref = source.get("reference", "")
            if ref:
                resource_type = ref.split("/")[0] if "/" in ref else None
                if resource_type in self.INFORMATION_SOURCE_MAP:
                    spec_data["information_source"] = self.INFORMATION_SOURCE_MAP[resource_type]

        # Map reason
        reason_codes = fhir_resource.get("reasonCode", [])
        if reason_codes:
            first_reason = reason_codes[0]
            if first_reason.get("text"):
                spec_data["reason"] = first_reason.get("text")
            elif first_reason.get("coding"):
                codings = first_reason.get("coding", [])
                if codings:
                    spec_data["reason"] = codings[0].get("display") or codings[0].get("code")

        # Map dosage text
        dosages = fhir_resource.get("dosage", [])
        if dosages:
            first_dosage = dosages[0]
            if first_dosage.get("text"):
                spec_data["dosage_text"] = first_dosage.get("text")
            else:
                # Try to construct dosage text from structured data
                dosage_parts = []
                if first_dosage.get("doseAndRate"):
                    dose_rate = first_dosage.get("doseAndRate", [{}])[0]
                    if dose_rate.get("doseQuantity"):
                        qty = dose_rate.get("doseQuantity", {})
                        dosage_parts.append(f"{qty.get('value')} {qty.get('unit', '')}")
                if first_dosage.get("timing"):
                    timing = first_dosage.get("timing", {})
                    if timing.get("code", {}).get("text"):
                        dosage_parts.append(timing.get("code", {}).get("text"))
                    elif timing.get("repeat"):
                        repeat = timing.get("repeat", {})
                        if repeat.get("frequency") and repeat.get("period"):
                            dosage_parts.append(
                                f"{repeat.get('frequency')} times per {repeat.get('period')} {repeat.get('periodUnit', '')}"
                            )
                if first_dosage.get("route", {}).get("text"):
                    dosage_parts.append(first_dosage.get("route", {}).get("text"))
                if dosage_parts:
                    spec_data["dosage_text"] = " - ".join(dosage_parts)

        # Map note
        notes = fhir_resource.get("note", [])
        if notes and notes[0].get("text"):
            spec_data["note"] = notes[0].get("text")

        return spec_data

    def _has_valid_medication(self, fhir_resource: dict[str, Any]) -> bool:
        """
        Check if the FHIR resource has a valid medication field.

        Args:
            fhir_resource: The FHIR MedicationStatement resource

        Returns:
            True if medication is present with valid data, False otherwise
        """
        # Check medicationCodeableConcept
        med_concept = fhir_resource.get("medicationCodeableConcept")
        if med_concept:
            codings = med_concept.get("coding", [])
            for coding in codings:
                if coding.get("code") or coding.get("display"):
                    return True
            if med_concept.get("text"):
                return True

        # Check medicationReference
        med_ref = fhir_resource.get("medicationReference")
        if med_ref:
            if med_ref.get("display") or med_ref.get("reference"):
                return True

        return False

    def validate_fhir_resource(self, fhir_resource: dict[str, Any]) -> list[str]:
        """
        Validate the FHIR MedicationStatement resource.

        Note: Medication validation is handled separately in process() to allow
        skipping instead of failing.

        Args:
            fhir_resource: The FHIR MedicationStatement resource

        Returns:
            List of validation errors
        """
        errors = super().validate_fhir_resource(fhir_resource)

        # Status is required
        if not fhir_resource.get("status"):
            errors.append("MedicationStatement.status is required")

        return errors

    def process(self, fhir_resource: dict[str, Any]) -> dict[str, Any]:
        """
        Process a FHIR MedicationStatement and create the care MedicationStatement.

        Overridden to bypass ValueSetBoundCoding validation for medication codes
        that may not exist in the care system's valuesets when importing from
        external FHIR systems.

        MedicationStatements without a valid medication are skipped (not failed).

        Args:
            fhir_resource: The FHIR MedicationStatement resource

        Returns:
            Processing result dictionary
        """
        result = {
            "success": False,
            "resource_type": self.resource_type,
            "fhir_id": fhir_resource.get("id"),
        }

        # Check if medication is present and valid - skip if not
        if not self._has_valid_medication(fhir_resource):
            logger.info(
                f"Skipping MedicationStatement without valid medication: {fhir_resource.get('id')}"
            )
            return {
                "success": True,
                "resource_type": self.resource_type,
                "fhir_id": fhir_resource.get("id"),
                "skipped": True,
                "message": "MedicationStatement without valid medication is not allowed and was skipped",
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
            model_instance = MedicationStatement()

            # Set basic fields
            model_instance.status = spec_data.get(
                "status", MedicationStatementStatus.active
            ).value

            # Set medication directly (bypassing ValueSetBoundCoding validation)
            model_instance.medication = spec_data.get("medication") or {}

            # Set effective_period
            model_instance.effective_period = spec_data.get("effective_period") or {}

            # Set information_source
            info_source = spec_data.get("information_source")
            if info_source:
                model_instance.information_source = info_source.value
            else:
                model_instance.information_source = MedicationStatementInformationSourceType.patient.value

            # Set reason
            model_instance.reason = spec_data.get("reason")

            # Set dosage_text
            model_instance.dosage_text = spec_data.get("dosage_text")

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
            logger.exception(f"Error processing FHIR MedicationStatement: {e}")
            result["errors"] = [str(e)]

        return result
