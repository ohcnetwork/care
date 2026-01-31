"""
FHIR Bundle Processor.

This module provides the main bundle processor that orchestrates
the processing of FHIR bundles and creation of care resources.
"""

import logging
from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction
from pydantic import UUID4
from rest_framework.exceptions import PermissionDenied

from care.emr.fhir.bundle.questionnaire_handler import FHIRQuestionnaireProcessor
from care.emr.fhir.bundle.registry import FHIRResourceRegistry
from care.emr.models import Encounter
from care.security.authorization import AuthorizationController
from care.utils.shortcuts import get_object_or_404

User = get_user_model()
logger = logging.getLogger(__name__)


class FHIRBundleProcessor:
    """
    Processor for FHIR bundles.

    This class orchestrates the processing of FHIR bundles by:
    1. Validating the bundle structure
    2. Authorizing access to the encounter
    3. Processing each resource entry using the appropriate processor
    4. Handling transactions (all-or-nothing semantics)

    Usage:
        processor = FHIRBundleProcessor(
            encounter_id=encounter_uuid,
            user=request.user
        )
        result = processor.process_bundle(bundle_data)
    """

    # Supported bundle types
    SUPPORTED_BUNDLE_TYPES = ["transaction", "batch", "collection"]

    # Resource types to skip (already present in context or not meaningful to store)
    SKIP_RESOURCE_TYPES = ["Encounter", "Patient", "Composition"]

    def __init__(
        self,
        encounter_id: UUID4 | str,
        user: User,
        use_questionnaire_fallback: bool = True,
    ):
        """
        Initialize the bundle processor.

        Args:
            encounter_id: The encounter UUID for context
            user: The user processing the bundle
            use_questionnaire_fallback: If True, unsupported FHIR resources
                will be stored as questionnaire responses. If False, they
                will be rejected with an error.

        Raises:
            Http404: If the encounter doesn't exist
            PermissionDenied: If the user doesn't have access
        """
        self.encounter = get_object_or_404(Encounter, external_id=encounter_id)
        self.user = user
        self.use_questionnaire_fallback = use_questionnaire_fallback
        self._authorize()

    def _authorize(self) -> None:
        """
        Authorize the user to update clinical data for the encounter.

        Raises:
            PermissionDenied: If the user doesn't have permission
        """
        if not AuthorizationController.call(
            "can_update_encounter_clinical_data", self.user, self.encounter
        ):
            raise PermissionDenied(
                "You do not have permission to update clinical data for this encounter"
            )

    def validate_bundle(self, bundle: dict[str, Any]) -> list[str]:
        """
        Validate the FHIR bundle structure.

        Args:
            bundle: The FHIR bundle data

        Returns:
            A list of validation error messages (empty if valid)
        """
        errors = []

        if bundle.get("resourceType") != "Bundle":
            errors.append(
                f"Expected resourceType 'Bundle', got '{bundle.get('resourceType')}'"
            )

        bundle_type = bundle.get("type")
        if bundle_type not in self.SUPPORTED_BUNDLE_TYPES:
            errors.append(
                f"Unsupported bundle type '{bundle_type}'. "
                f"Supported types: {self.SUPPORTED_BUNDLE_TYPES}"
            )

        entries = bundle.get("entry", [])
        if not entries:
            errors.append("Bundle must contain at least one entry")

        return errors

    def process_bundle(
        self, bundle: dict[str, Any], fail_on_error: bool = True
    ) -> dict[str, Any]:
        """
        Process a FHIR bundle and create care resources.

        Args:
            bundle: The FHIR bundle data
            fail_on_error: If True, roll back all changes on any error (transaction)
                          If False, process all entries and report individual errors (batch)

        Returns:
            A dictionary containing:
            - success: bool - Overall success status
            - bundle_type: str - The bundle type processed
            - total_entries: int - Total number of entries
            - processed: int - Number of successfully processed entries
            - failed: int - Number of failed entries
            - results: list - Individual results for each entry
            - errors: list - Bundle-level errors (if any)
        """
        result = {
            "success": False,
            "bundle_type": bundle.get("type"),
            "total_entries": 0,
            "processed": 0,
            "failed": 0,
            "results": [],
            "errors": [],
        }

        # Validate bundle structure
        validation_errors = self.validate_bundle(bundle)
        if validation_errors:
            result["errors"] = validation_errors
            return result

        entries = bundle.get("entry", [])
        result["total_entries"] = len(entries)

        # Determine processing mode based on bundle type
        bundle_type = bundle.get("type")
        is_transaction = bundle_type == "transaction" or fail_on_error

        if is_transaction:
            return self._process_transaction(entries, result)
        else:
            return self._process_batch(entries, result)

    def _process_transaction(
        self, entries: list[dict], result: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Process entries as a transaction (all-or-nothing).

        Args:
            entries: List of bundle entries
            result: The result dictionary to populate

        Returns:
            The populated result dictionary
        """
        try:
            with transaction.atomic():
                for entry in entries:
                    entry_result = self._process_entry(entry)
                    result["results"].append(entry_result)

                    if entry_result["success"]:
                        result["processed"] += 1
                    else:
                        result["failed"] += 1
                        # For transactions, any failure causes rollback
                        raise TransactionRollback(
                            f"Entry failed: {entry_result.get('errors', [])}"
                        )

                result["success"] = True

        except TransactionRollback:
            # Transaction was rolled back due to entry failure
            result["success"] = False
            result["errors"].append(
                "Transaction rolled back due to entry processing failure"
            )

        return result

    def _process_batch(
        self, entries: list[dict], result: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Process entries as a batch (independent processing).

        Args:
            entries: List of bundle entries
            result: The result dictionary to populate

        Returns:
            The populated result dictionary
        """
        for entry in entries:
            try:
                with transaction.atomic():
                    entry_result = self._process_entry(entry)
                    result["results"].append(entry_result)

                    if entry_result["success"]:
                        result["processed"] += 1
                    else:
                        result["failed"] += 1

            except Exception as e:
                logger.exception(f"Error processing batch entry: {e}")
                result["results"].append({
                    "success": False,
                    "resource_type": entry.get("resource", {}).get("resourceType"),
                    "errors": [str(e)],
                })
                result["failed"] += 1

        result["success"] = result["failed"] == 0
        return result

    def _process_entry(self, entry: dict[str, Any]) -> dict[str, Any]:
        """
        Process a single bundle entry.

        If the resource type is not directly supported and questionnaire
        fallback is enabled, the resource will be stored as a questionnaire
        response.

        Args:
            entry: The bundle entry containing a FHIR resource

        Returns:
            The processing result for this entry
        """
        resource = entry.get("resource")
        if not resource:
            return {
                "success": False,
                "errors": ["Entry does not contain a resource"],
            }

        resource_type = resource.get("resourceType")
        if not resource_type:
            return {
                "success": False,
                "errors": ["Resource does not have a resourceType"],
            }

        # Skip resource types that are already present in context or not meaningful to store
        if resource_type in self.SKIP_RESOURCE_TYPES:
            logger.debug(
                f"Skipping {resource_type} resource"
            )
            # Provide appropriate skip message based on resource type
            if resource_type in ("Patient", "Encounter"):
                message = f"{resource_type} resources are not processed as they are already present in the encounter context"
            elif resource_type == "Composition":
                message = "Composition resources describe document structure and are not stored"
            else:
                message = f"{resource_type} resources are skipped"

            return {
                "success": True,
                "resource_type": resource_type,
                "fhir_id": resource.get("id"),
                "skipped": True,
                "message": message,
            }

        # Get the processor for this resource type
        processor_class = FHIRResourceRegistry.get(resource_type)

        if processor_class:
            # Use the dedicated processor for this resource type
            processor = processor_class(self.encounter, self.user)
            return processor.process(resource)

        # No dedicated processor found - check if we should use fallback
        if self.use_questionnaire_fallback:
            # Use the questionnaire fallback processor
            logger.info(
                f"Using questionnaire fallback for unsupported resource type: "
                f"{resource_type}"
            )
            fallback_processor = FHIRQuestionnaireProcessor(
                self.encounter, self.user
            )
            return fallback_processor.process(resource)

        # Fallback disabled - return error
        return {
            "success": False,
            "resource_type": resource_type,
            "fhir_id": resource.get("id"),
            "errors": [
                f"Unsupported resource type: {resource_type}. "
                f"Supported types: {FHIRResourceRegistry.get_supported_types()}"
            ],
        }


class TransactionRollback(Exception):
    """
    Exception raised to trigger transaction rollback.

    This is used internally to trigger a rollback when processing
    a transaction bundle and an entry fails.
    """

    pass
