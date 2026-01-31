"""
FHIR ServiceRequest Resource Processor.

Maps FHIR ServiceRequest resources to care ServiceRequest specs.
"""

import logging
from typing import Any

from dateutil.parser import parse as parse_datetime
from pydantic import UUID4

from care.emr.fhir.bundle.base import FHIRResourceProcessor
from care.emr.fhir.bundle.registry import register_processor
from care.emr.models.service_request import ServiceRequest
from care.emr.resources.activity_definition.spec import (
    ActivityDefinitionCategoryOptions,
)
from care.emr.resources.service_request.spec import (
    ServiceRequestCreateSpec,
    ServiceRequestIntentChoices,
    ServiceRequestPriorityChoices,
    ServiceRequestStatusChoices,
)

logger = logging.getLogger(__name__)


@register_processor
class ServiceRequestProcessor(FHIRResourceProcessor):
    """
    Processor for FHIR ServiceRequest resources.

    Maps FHIR ServiceRequest to care ServiceRequest model.

    FHIR ServiceRequest Reference:
    https://www.hl7.org/fhir/servicerequest.html
    """

    resource_type = "ServiceRequest"
    pydantic_spec = ServiceRequestCreateSpec

    # Mapping from FHIR status to care enum
    STATUS_MAP = {
        "draft": ServiceRequestStatusChoices.draft,
        "active": ServiceRequestStatusChoices.active,
        "on-hold": ServiceRequestStatusChoices.on_hold,
        "entered-in-error": ServiceRequestStatusChoices.entered_in_error,
        "completed": ServiceRequestStatusChoices.completed,
        "revoked": ServiceRequestStatusChoices.revoked,
    }

    # Mapping from FHIR intent to care enum
    INTENT_MAP = {
        "proposal": ServiceRequestIntentChoices.proposal,
        "plan": ServiceRequestIntentChoices.plan,
        "directive": ServiceRequestIntentChoices.directive,
        "order": ServiceRequestIntentChoices.order,
    }

    # Mapping from FHIR priority to care enum
    PRIORITY_MAP = {
        "routine": ServiceRequestPriorityChoices.routine,
        "urgent": ServiceRequestPriorityChoices.urgent,
        "asap": ServiceRequestPriorityChoices.asap,
        "stat": ServiceRequestPriorityChoices.stat,
    }

    # Mapping from FHIR category to care enum
    CATEGORY_MAP = {
        "laboratory": ActivityDefinitionCategoryOptions.laboratory,
        "imaging": ActivityDefinitionCategoryOptions.imaging,
        "procedure": ActivityDefinitionCategoryOptions.surgical_procedure,
        "consultation": ActivityDefinitionCategoryOptions.counselling,
        "counselling": ActivityDefinitionCategoryOptions.counselling,
        "surgical-procedure": ActivityDefinitionCategoryOptions.surgical_procedure,
    }

    def map_fhir_to_spec(
        self, fhir_resource: dict[str, Any], encounter_id: UUID4
    ) -> dict[str, Any]:
        """
        Map FHIR ServiceRequest to care ServiceRequestCreateSpec format.

        Args:
            fhir_resource: The FHIR ServiceRequest resource
            encounter_id: The encounter UUID

        Returns:
            Dictionary for ServiceRequestCreateSpec validation
        """
        spec_data = {
            "encounter": encounter_id,
        }

        # Map status (required)
        status = fhir_resource.get("status", "active")
        spec_data["status"] = self.STATUS_MAP.get(
            status, ServiceRequestStatusChoices.active
        )

        # Map intent (required)
        intent = fhir_resource.get("intent", "order")
        spec_data["intent"] = self.INTENT_MAP.get(
            intent, ServiceRequestIntentChoices.order
        )

        # Map priority
        priority = fhir_resource.get("priority", "routine")
        spec_data["priority"] = self.PRIORITY_MAP.get(
            priority, ServiceRequestPriorityChoices.routine
        )

        # Map category
        categories = fhir_resource.get("category", [])
        if categories:
            category_code = self._extract_coding_code(categories[0])
            spec_data["category"] = self.CATEGORY_MAP.get(
                category_code, ActivityDefinitionCategoryOptions.laboratory
            )
        else:
            spec_data["category"] = ActivityDefinitionCategoryOptions.laboratory

        # Map do_not_perform
        spec_data["do_not_perform"] = fhir_resource.get("doNotPerform", False)

        # Map code (required)
        code = fhir_resource.get("code")
        if code:
            spec_data["code"] = self.map_codeable_concept_to_coding(code)

        # Map title from code display or text
        if code:
            codings = code.get("coding", [])
            if codings and codings[0].get("display"):
                spec_data["title"] = codings[0].get("display")
            elif code.get("text"):
                spec_data["title"] = code.get("text")
            else:
                spec_data["title"] = "Service Request"
        else:
            spec_data["title"] = "Service Request"

        # Map body site
        body_sites = fhir_resource.get("bodySite", [])
        if body_sites:
            spec_data["body_site"] = self.map_codeable_concept_to_coding(body_sites[0])

        # Map occurrence datetime
        if fhir_resource.get("occurrenceDateTime"):
            spec_data["occurance"] = fhir_resource.get("occurrenceDateTime")
        elif fhir_resource.get("occurrencePeriod"):
            period = fhir_resource.get("occurrencePeriod", {})
            spec_data["occurance"] = period.get("start")

        # Map patient instruction
        if fhir_resource.get("patientInstruction"):
            spec_data["patient_instruction"] = fhir_resource.get("patientInstruction")

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

    def validate_fhir_resource(self, fhir_resource: dict[str, Any]) -> list[str]:
        """
        Validate the FHIR ServiceRequest resource.

        Args:
            fhir_resource: The FHIR ServiceRequest resource

        Returns:
            List of validation errors
        """
        errors = super().validate_fhir_resource(fhir_resource)

        # Status is required
        if not fhir_resource.get("status"):
            errors.append("ServiceRequest.status is required")

        # Intent is required
        if not fhir_resource.get("intent"):
            errors.append("ServiceRequest.intent is required")

        # Code is required
        if not fhir_resource.get("code"):
            errors.append("ServiceRequest.code is required")

        return errors

    def process(self, fhir_resource: dict[str, Any]) -> dict[str, Any]:
        """
        Process a FHIR ServiceRequest and create the care ServiceRequest.

        Overridden to bypass ValueSetBoundCoding validation for codes
        that may not exist in the care system's valuesets when importing from
        external FHIR systems.

        Args:
            fhir_resource: The FHIR ServiceRequest resource

        Returns:
            Processing result dictionary
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

            # Create the model instance directly to bypass ValueSetBoundCoding validation
            model_instance = ServiceRequest()

            # Set basic fields
            model_instance.title = spec_data.get("title", "Service Request")
            model_instance.status = spec_data.get(
                "status", ServiceRequestStatusChoices.active
            ).value
            model_instance.intent = spec_data.get(
                "intent", ServiceRequestIntentChoices.order
            ).value
            model_instance.priority = spec_data.get(
                "priority", ServiceRequestPriorityChoices.routine
            ).value
            model_instance.category = spec_data.get(
                "category", ActivityDefinitionCategoryOptions.laboratory
            ).value
            model_instance.do_not_perform = spec_data.get("do_not_perform", False)

            # Set code directly (bypassing ValueSetBoundCoding validation)
            model_instance.code = spec_data.get("code")

            # Set body_site directly (bypassing ValueSetBoundCoding validation)
            model_instance.body_site = spec_data.get("body_site")

            # Set occurrence
            occurance = spec_data.get("occurance")
            if occurance:
                if isinstance(occurance, str):
                    model_instance.occurance = parse_datetime(occurance)
                else:
                    model_instance.occurance = occurance

            # Set patient instruction
            model_instance.patient_instruction = spec_data.get("patient_instruction")

            # Set note
            model_instance.note = spec_data.get("note")

            # Set encounter, patient, and facility
            model_instance.encounter = self.encounter
            model_instance.patient = self.encounter.patient
            model_instance.facility = self.encounter.facility

            # Set audit fields
            model_instance.created_by = self.user
            model_instance.updated_by = self.user
            model_instance.requester = self.user

            # Save the instance
            model_instance.save()

            result["success"] = True
            result["care_id"] = str(model_instance.external_id)

        except Exception as e:
            logger.exception(f"Error processing FHIR ServiceRequest: {e}")
            result["errors"] = [str(e)]

        return result
