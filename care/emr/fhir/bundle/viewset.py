"""
FHIR Bundle Processing ViewSet.

Provides an API endpoint for processing FHIR bundles within an encounter context.
"""

import logging

from drf_spectacular.utils import OpenApiParameter, extend_schema
from pydantic import ValidationError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.emr.api.viewsets.base import emr_exception_handler

# Import processors to register them
from care.emr.fhir.bundle import processors as _processors  # noqa: F401
from care.emr.fhir.bundle.processor import FHIRBundleProcessor
from care.emr.fhir.bundle.registry import FHIRResourceRegistry
from care.emr.fhir.bundle.spec import (
    FHIRBundleProcessRequest,
    FHIRBundleRequest,
    FHIRBundleResponse,
)

logger = logging.getLogger(__name__)


class FHIRBundleViewSet(GenericViewSet):
    """
    ViewSet for processing FHIR bundles.

    This endpoint accepts FHIR bundles and creates the corresponding
    resources in the care system. All resources are associated with
    the specified encounter.

    Supported Resource Types:
    - Condition
    - Observation
    - MedicationRequest
    - AllergyIntolerance
    - ServiceRequest

    Authorization:
    - Requires permission to update clinical data for the encounter

    Bundle Types:
    - transaction: All-or-nothing - if any entry fails, all changes are rolled back
    - batch: Independent processing - each entry is processed separately
    - collection: Treated as batch for processing purposes

    Example Request:
        POST /api/v1/fhir/bundle/process/
        {
            "encounter": "uuid-of-encounter",
            "bundle": {
                "resourceType": "Bundle",
                "type": "transaction",
                "entry": [
                    {
                        "resource": {
                            "resourceType": "Condition",
                            "code": {
                                "coding": [{
                                    "system": "http://snomed.info/sct",
                                    "code": "38341003",
                                    "display": "Hypertension"
                                }]
                            },
                            "verificationStatus": {
                                "coding": [{
                                    "code": "confirmed"
                                }]
                            },
                            "category": [{
                                "coding": [{
                                    "code": "encounter-diagnosis"
                                }]
                            }]
                        }
                    }
                ]
            }
        }
    """

    def get_exception_handler(self):
        return emr_exception_handler

    @extend_schema(
        summary="Get supported FHIR resource types",
        description="Returns a list of FHIR resource types that can be processed by this endpoint.",
        responses={200: dict},
    )
    def list(self, request, *args, **kwargs):
        """
        List supported FHIR resource types.

        Returns the resource types that can be included in a FHIR bundle
        for processing. Also indicates support for questionnaire fallback
        for unsupported resource types.
        """
        return Response({
            "supported_resource_types": FHIRResourceRegistry.get_supported_types(),
            "supported_bundle_types": ["transaction", "batch", "collection"],
            "skipped_resource_types": {
                "types": ["Encounter", "Patient", "Composition"],
                "description": (
                    "These resource types are automatically skipped. "
                    "Patient/Encounter are already in context, "
                    "Composition describes document structure and is not stored."
                ),
            },
            "questionnaire_fallback": {
                "enabled_by_default": True,
                "description": (
                    "Unsupported FHIR resource types can be stored as "
                    "questionnaire responses when 'use_questionnaire_fallback' "
                    "is set to true. The full FHIR resource data is preserved."
                ),
            },
        })

    @extend_schema(
        summary="Process a FHIR bundle",
        description=(
            "Process a FHIR bundle and create resources within an encounter context. "
            "The bundle should contain entries with FHIR resources that will be mapped "
            "to care system resources. Authorization is checked at the encounter level."
        ),
        request=FHIRBundleProcessRequest,
        responses={
            200: FHIRBundleResponse,
            400: dict,
            403: dict,
            404: dict,
        },
    )
    @action(detail=False, methods=["POST"])
    def process(self, request, *args, **kwargs):
        """
        Process a FHIR bundle and create care resources.

        This endpoint accepts a FHIR bundle along with an encounter ID and
        processes all entries in the bundle, creating the corresponding
        resources in the care system.

        All resources are associated with the specified encounter, and
        authorization is checked at the encounter level.

        Bundle processing modes:
        - transaction (default): All-or-nothing semantics. If any entry fails,
          all changes are rolled back.
        - batch: Each entry is processed independently. Failures don't affect
          other entries.

        Returns:
            JSON response with processing results for each entry
        """
        try:
            # Validate request
            process_request = FHIRBundleProcessRequest.model_validate(request.data)
        except ValidationError as e:
            return Response(
                {"errors": e.errors()},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Initialize the bundle processor (performs authorization)
            processor = FHIRBundleProcessor(
                encounter_id=process_request.encounter,
                user=request.user,
                use_questionnaire_fallback=process_request.use_questionnaire_fallback,
            )

            # Process the bundle
            bundle_dict = process_request.bundle.model_dump(mode="json")
            result = processor.process_bundle(
                bundle_dict,
                fail_on_error=process_request.fail_on_error,
            )

            # Add encounter ID to response
            result["encounter_id"] = str(process_request.encounter)
            result["questionnaire_fallback_enabled"] = process_request.use_questionnaire_fallback

            # Determine response status
            if result["success"]:
                return Response(result, status=status.HTTP_200_OK)
            elif result.get("errors"):
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
            else:
                # Partial success in batch mode
                return Response(result, status=status.HTTP_207_MULTI_STATUS)

        except Exception as e:
            logger.exception(f"Error processing FHIR bundle: {e}")
            return Response(
                {"errors": [{"type": "processing_error", "msg": str(e)}]},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        summary="Process a FHIR bundle directly",
        description=(
            "Alternative endpoint that accepts a FHIR bundle directly with the "
            "encounter specified as a query parameter."
        ),
        parameters=[
            OpenApiParameter(
                name="encounter",
                description="The encounter UUID to associate resources with",
                required=True,
                type=str,
            ),
            OpenApiParameter(
                name="fail_on_error",
                description="If true, roll back all changes on any error",
                required=False,
                type=bool,
                default=True,
            ),
            OpenApiParameter(
                name="use_questionnaire_fallback",
                description=(
                    "If true, unsupported FHIR resources will be stored "
                    "as questionnaire responses"
                ),
                required=False,
                type=bool,
                default=True,
            ),
        ],
        request=FHIRBundleRequest,
        responses={
            200: FHIRBundleResponse,
            400: dict,
            403: dict,
            404: dict,
        },
    )
    def create(self, request, *args, **kwargs):
        """
        Process a FHIR bundle directly.

        Alternative to the /process/ endpoint that accepts the bundle directly
        in the request body with the encounter specified as a query parameter.
        """
        encounter_id = request.query_params.get("encounter")
        if not encounter_id:
            return Response(
                {"errors": [{"type": "validation_error", "msg": "encounter query parameter is required"}]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        fail_on_error = request.query_params.get("fail_on_error", "true").lower() == "true"
        use_questionnaire_fallback = request.query_params.get(
            "use_questionnaire_fallback", "true"
        ).lower() == "true"

        try:
            # Validate bundle
            bundle = FHIRBundleRequest.model_validate(request.data)
        except ValidationError as e:
            return Response(
                {"errors": e.errors()},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Initialize the bundle processor (performs authorization)
            processor = FHIRBundleProcessor(
                encounter_id=encounter_id,
                user=request.user,
                use_questionnaire_fallback=use_questionnaire_fallback,
            )

            # Process the bundle
            bundle_dict = bundle.model_dump(mode="json")
            result = processor.process_bundle(bundle_dict, fail_on_error=fail_on_error)

            # Add encounter ID to response
            result["encounter_id"] = encounter_id
            result["questionnaire_fallback_enabled"] = use_questionnaire_fallback

            # Determine response status
            if result["success"]:
                return Response(result, status=status.HTTP_200_OK)
            elif result.get("errors"):
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response(result, status=status.HTTP_207_MULTI_STATUS)

        except Exception as e:
            logger.exception(f"Error processing FHIR bundle: {e}")
            return Response(
                {"errors": [{"type": "processing_error", "msg": str(e)}]},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
