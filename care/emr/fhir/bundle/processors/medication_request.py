"""
FHIR MedicationRequest Resource Processor.

Maps FHIR MedicationRequest resources to care MedicationRequest specs.
"""

import logging
from datetime import datetime
from typing import Any

from dateutil.parser import parse as parse_datetime
from pydantic import UUID4

from care.emr.fhir.bundle.base import FHIRResourceProcessor
from care.emr.fhir.bundle.registry import register_processor
from care.emr.models.medication_request import MedicationRequest
from care.emr.resources.medication.request.spec import (
    DosageInstruction,
    DosageQuantity,
    DoseAndRate,
    DoseRange,
    DoseType,
    MedicationRequestCategory,
    MedicationRequestIntent,
    MedicationRequestPriority,
    MedicationRequestSpec,
    MedicationRequestStatus,
    Timing,
    TimingQuantity,
    TimingRepeat,
    TimingUnit,
)

logger = logging.getLogger(__name__)


@register_processor
class MedicationRequestProcessor(FHIRResourceProcessor):
    """
    Processor for FHIR MedicationRequest resources.

    Maps FHIR MedicationRequest to care MedicationRequest model.

    FHIR MedicationRequest Reference:
    https://www.hl7.org/fhir/medicationrequest.html
    """

    resource_type = "MedicationRequest"
    pydantic_spec = MedicationRequestSpec

    # Mapping from FHIR status to care enum
    STATUS_MAP = {
        "active": MedicationRequestStatus.active,
        "on-hold": MedicationRequestStatus.on_hold,
        "ended": MedicationRequestStatus.ended,
        "stopped": MedicationRequestStatus.stopped,
        "completed": MedicationRequestStatus.completed,
        "cancelled": MedicationRequestStatus.cancelled,
        "entered-in-error": MedicationRequestStatus.entered_in_error,
        "draft": MedicationRequestStatus.draft,
        "unknown": MedicationRequestStatus.unknown,
    }

    # Mapping from FHIR intent to care enum
    INTENT_MAP = {
        "proposal": MedicationRequestIntent.proposal,
        "plan": MedicationRequestIntent.plan,
        "order": MedicationRequestIntent.order,
        "original-order": MedicationRequestIntent.original_order,
        "reflex-order": MedicationRequestIntent.reflex_order,
        "filler-order": MedicationRequestIntent.filler_order,
        "instance-order": MedicationRequestIntent.instance_order,
    }

    # Mapping from FHIR priority to care enum
    PRIORITY_MAP = {
        "routine": MedicationRequestPriority.routine,
        "urgent": MedicationRequestPriority.urgent,
        "asap": MedicationRequestPriority.asap,
        "stat": MedicationRequestPriority.stat,
    }

    # Mapping from FHIR category to care enum
    CATEGORY_MAP = {
        "inpatient": MedicationRequestCategory.inpatient,
        "outpatient": MedicationRequestCategory.outpatient,
        "community": MedicationRequestCategory.community,
        "discharge": MedicationRequestCategory.discharge,
    }

    # Mapping from FHIR timing unit to care enum
    TIMING_UNIT_MAP = {
        "s": TimingUnit.s,
        "min": TimingUnit.min,
        "h": TimingUnit.h,
        "d": TimingUnit.d,
        "wk": TimingUnit.wk,
        "mo": TimingUnit.mo,
        "a": TimingUnit.a,
    }

    def map_fhir_to_spec(
        self, fhir_resource: dict[str, Any], encounter_id: UUID4
    ) -> dict[str, Any]:
        """
        Map FHIR MedicationRequest to care MedicationRequestSpec format.

        Args:
            fhir_resource: The FHIR MedicationRequest resource
            encounter_id: The encounter UUID

        Returns:
            Dictionary for MedicationRequestSpec validation
        """
        spec_data = {
            "encounter": encounter_id,
        }

        # Map status (required)
        status = fhir_resource.get("status", "active")
        spec_data["status"] = self.STATUS_MAP.get(status, MedicationRequestStatus.active)

        # Map intent (required)
        intent = fhir_resource.get("intent", "order")
        spec_data["intent"] = self.INTENT_MAP.get(intent, MedicationRequestIntent.order)

        # Map priority
        priority = fhir_resource.get("priority", "routine")
        spec_data["priority"] = self.PRIORITY_MAP.get(
            priority, MedicationRequestPriority.routine
        )

        # Map category
        categories = fhir_resource.get("category", [])
        if categories:
            category_code = self._extract_coding_code(categories[0])
            spec_data["category"] = self.CATEGORY_MAP.get(
                category_code, MedicationRequestCategory.inpatient
            )
        else:
            spec_data["category"] = MedicationRequestCategory.inpatient

        # Map do_not_perform
        spec_data["do_not_perform"] = fhir_resource.get("doNotPerform", False)

        # Map medication
        medication = self._map_medication(fhir_resource)
        if medication:
            spec_data["medication"] = medication

        # Map dosage instructions
        dosage_instructions = fhir_resource.get("dosageInstruction", [])
        spec_data["dosage_instruction"] = [
            self._map_dosage_instruction(di) for di in dosage_instructions
        ]

        # Ensure at least one dosage instruction
        if not spec_data["dosage_instruction"]:
            spec_data["dosage_instruction"] = [{"as_needed_boolean": False}]

        # Map authored_on
        if fhir_resource.get("authoredOn"):
            spec_data["authored_on"] = fhir_resource.get("authoredOn")
        else:
            spec_data["authored_on"] = datetime.now().isoformat()

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

    def _map_medication(self, fhir_resource: dict[str, Any]) -> dict | None:
        """
        Map FHIR medication reference or CodeableConcept.

        Args:
            fhir_resource: The FHIR MedicationRequest resource

        Returns:
            Care medication coding or None
        """
        # Try medicationCodeableConcept first
        if fhir_resource.get("medicationCodeableConcept"):
            return self.map_codeable_concept_to_coding(
                fhir_resource.get("medicationCodeableConcept")
            )

        # Try medicationReference
        if fhir_resource.get("medicationReference"):
            # This would need to resolve the reference
            # For now, extract display if available
            ref = fhir_resource.get("medicationReference", {})
            if ref.get("display"):
                return {"display": ref.get("display")}

        return None

    def _map_dosage_instruction(self, dosage: dict[str, Any]) -> dict[str, Any]:
        """
        Map FHIR Dosage to care DosageInstruction format.

        Args:
            dosage: FHIR Dosage

        Returns:
            Care DosageInstruction dictionary
        """
        instruction = {
            "as_needed_boolean": dosage.get("asNeededBoolean", False),
        }

        # Map sequence
        if dosage.get("sequence"):
            instruction["sequence"] = dosage.get("sequence")

        # Map text
        if dosage.get("text"):
            instruction["text"] = dosage.get("text")

        # Map patient instruction
        if dosage.get("patientInstruction"):
            instruction["patient_instruction"] = dosage.get("patientInstruction")

        # Map additional instruction
        additional_instructions = dosage.get("additionalInstruction", [])
        if additional_instructions:
            instruction["additional_instruction"] = [
                self.map_codeable_concept_to_coding(ai)
                for ai in additional_instructions
                if self.map_codeable_concept_to_coding(ai)
            ]

        # Map timing
        timing = dosage.get("timing")
        if timing:
            mapped_timing = self._map_timing(timing)
            if mapped_timing:
                instruction["timing"] = mapped_timing

        # Map as_needed_for (asNeededCodeableConcept)
        if dosage.get("asNeededCodeableConcept"):
            instruction["as_needed_for"] = self.map_codeable_concept_to_coding(
                dosage.get("asNeededCodeableConcept")
            )

        # Map site
        if dosage.get("site"):
            instruction["site"] = self.map_codeable_concept_to_coding(
                dosage.get("site")
            )

        # Map route
        if dosage.get("route"):
            instruction["route"] = self.map_codeable_concept_to_coding(
                dosage.get("route")
            )

        # Map method
        if dosage.get("method"):
            instruction["method"] = self.map_codeable_concept_to_coding(
                dosage.get("method")
            )

        # Map doseAndRate
        dose_and_rate = dosage.get("doseAndRate", [])
        if dose_and_rate:
            instruction["dose_and_rate"] = self._map_dose_and_rate(dose_and_rate[0])

        # Map maxDosePerPeriod
        if dosage.get("maxDosePerPeriod"):
            instruction["max_dose_per_period"] = self._map_dose_range_from_ratio(
                dosage.get("maxDosePerPeriod")
            )

        return instruction

    def _map_timing(self, timing: dict[str, Any]) -> dict | None:
        """
        Map FHIR Timing to care Timing format.

        Args:
            timing: FHIR Timing

        Returns:
            Care Timing dictionary or None
        """
        result = {}

        # Map repeat
        repeat = timing.get("repeat", {})
        if repeat:
            mapped_repeat = {
                "frequency": repeat.get("frequency", 1),
                "period": repeat.get("period", 1),
                "period_unit": self.TIMING_UNIT_MAP.get(
                    repeat.get("periodUnit", "d"), TimingUnit.d
                ),
            }

            # Map bounds duration
            if repeat.get("boundsDuration"):
                duration = repeat.get("boundsDuration", {})
                mapped_repeat["bounds_duration"] = {
                    "value": duration.get("value", 1),
                    "unit": self.TIMING_UNIT_MAP.get(
                        duration.get("code", "d"), TimingUnit.d
                    ),
                }
            else:
                # Default bounds duration
                mapped_repeat["bounds_duration"] = {
                    "value": 1,
                    "unit": TimingUnit.d,
                }

            result["repeat"] = mapped_repeat

        # Map code
        if timing.get("code"):
            result["code"] = self.map_codeable_concept_to_coding(timing.get("code"))
        else:
            result["code"] = {"code": "daily", "display": "Daily"}

        if "repeat" in result:
            return result
        return None

    def _map_dose_and_rate(self, dose_and_rate: dict[str, Any]) -> dict[str, Any]:
        """
        Map FHIR doseAndRate to care DoseAndRate format.

        Args:
            dose_and_rate: FHIR doseAndRate

        Returns:
            Care DoseAndRate dictionary
        """
        result = {
            "type": DoseType.ordered,
        }

        # Map type
        if dose_and_rate.get("type"):
            type_code = self._extract_coding_code(dose_and_rate.get("type"))
            if type_code == "calculated":
                result["type"] = DoseType.calculated

        # Map doseQuantity
        if dose_and_rate.get("doseQuantity"):
            quantity = dose_and_rate.get("doseQuantity", {})
            result["dose_quantity"] = {
                "value": quantity.get("value"),
                "unit": {
                    "code": quantity.get("code") or quantity.get("unit"),
                    "display": quantity.get("unit"),
                    "system": quantity.get("system"),
                },
            }

        # Map doseRange
        if dose_and_rate.get("doseRange"):
            range_val = dose_and_rate.get("doseRange", {})
            result["dose_range"] = {
                "low": self._map_dosage_quantity(range_val.get("low")),
                "high": self._map_dosage_quantity(range_val.get("high")),
            }

        return result

    def _map_dosage_quantity(self, quantity: dict | None) -> dict | None:
        """
        Map FHIR Quantity to care DosageQuantity format.

        Args:
            quantity: FHIR Quantity

        Returns:
            Care DosageQuantity dictionary or None
        """
        if not quantity:
            return None

        return {
            "value": quantity.get("value"),
            "unit": {
                "code": quantity.get("code") or quantity.get("unit"),
                "display": quantity.get("unit"),
                "system": quantity.get("system"),
            },
        }

    def _map_dose_range_from_ratio(self, ratio: dict[str, Any]) -> dict | None:
        """
        Map FHIR Ratio to care DoseRange format.

        Args:
            ratio: FHIR Ratio

        Returns:
            Care DoseRange dictionary or None
        """
        if not ratio:
            return None

        numerator = ratio.get("numerator")
        denominator = ratio.get("denominator")

        if numerator and denominator:
            return {
                "low": self._map_dosage_quantity(denominator),
                "high": self._map_dosage_quantity(numerator),
            }

        return None

    def validate_fhir_resource(self, fhir_resource: dict[str, Any]) -> list[str]:
        """
        Validate the FHIR MedicationRequest resource.

        Note: Medication validation is handled separately in process() to allow
        skipping instead of failing.

        Args:
            fhir_resource: The FHIR MedicationRequest resource

        Returns:
            List of validation errors
        """
        errors = super().validate_fhir_resource(fhir_resource)

        # Status is required
        if not fhir_resource.get("status"):
            errors.append("MedicationRequest.status is required")

        # Intent is required
        if not fhir_resource.get("intent"):
            errors.append("MedicationRequest.intent is required")

        # Note: Medication validation moved to process() to allow skipping

        return errors

    def _has_medication(self, fhir_resource: dict[str, Any]) -> bool:
        """
        Check if the FHIR resource has a medication field.

        Args:
            fhir_resource: The FHIR MedicationRequest resource

        Returns:
            True if medication is present, False otherwise
        """
        return bool(
            fhir_resource.get("medicationCodeableConcept")
            or fhir_resource.get("medicationReference")
        )

    def process(self, fhir_resource: dict[str, Any]) -> dict[str, Any]:
        """
        Process a FHIR MedicationRequest and create the care MedicationRequest.

        Overridden to bypass ValueSetBoundCoding validation for medication codes
        that may not exist in the care system's valuesets when importing from
        external FHIR systems.

        MedicationRequests without a medication field are skipped (not failed).

        Args:
            fhir_resource: The FHIR MedicationRequest resource

        Returns:
            Processing result dictionary
        """
        result = {
            "success": False,
            "resource_type": self.resource_type,
            "fhir_id": fhir_resource.get("id"),
        }

        # Check if medication is present - skip if not
        if not self._has_medication(fhir_resource):
            logger.info(
                f"Skipping MedicationRequest without medication: {fhir_resource.get('id')}"
            )
            return {
                "success": True,
                "resource_type": self.resource_type,
                "fhir_id": fhir_resource.get("id"),
                "skipped": True,
                "message": "MedicationRequest without medication is not allowed and was skipped",
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
            model_instance = MedicationRequest()

            # Set basic fields
            model_instance.status = spec_data.get("status", MedicationRequestStatus.active).value
            model_instance.intent = spec_data.get("intent", MedicationRequestIntent.order).value
            model_instance.category = spec_data.get("category", MedicationRequestCategory.inpatient).value
            model_instance.priority = spec_data.get("priority", MedicationRequestPriority.routine).value
            model_instance.do_not_perform = spec_data.get("do_not_perform", False)

            # Set medication directly (bypassing ValueSetBoundCoding validation)
            model_instance.medication = spec_data.get("medication")

            # Set dosage instruction
            model_instance.dosage_instruction = spec_data.get("dosage_instruction", [])

            # Set authored_on
            authored_on = spec_data.get("authored_on")
            if isinstance(authored_on, str):
                model_instance.authored_on = parse_datetime(authored_on)
            else:
                model_instance.authored_on = authored_on or datetime.now()

            # Set note
            model_instance.note = spec_data.get("note")

            # Set encounter and patient
            model_instance.encounter = self.encounter
            model_instance.patient = self.encounter.patient

            # Set audit fields
            model_instance.created_by = self.user
            model_instance.updated_by = self.user
            model_instance.requester = self.user

            # Save the instance
            model_instance.save()

            result["success"] = True
            result["care_id"] = str(model_instance.external_id)

        except Exception as e:
            logger.exception(f"Error processing FHIR MedicationRequest: {e}")
            result["errors"] = [str(e)]

        return result
