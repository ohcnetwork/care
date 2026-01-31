"""
Pydantic specifications for FHIR bundle request and response.

These specs define the structure of FHIR bundles accepted by the
bundle processing endpoint.
"""

from enum import Enum
from typing import Any

from pydantic import UUID4, BaseModel, Field


class FHIRBundleType(str, Enum):
    """Supported FHIR bundle types."""

    transaction = "transaction"
    batch = "batch"
    collection = "collection"


class FHIRBundleEntryRequest(BaseModel):
    """
    Request element in a bundle entry.

    Used in transaction and batch bundles to specify the HTTP method
    and URL for the operation.
    """

    method: str | None = None
    url: str | None = None


class FHIRBundleEntry(BaseModel):
    """
    A single entry in a FHIR bundle.

    Contains the resource to be processed and optional request metadata.
    """

    fullUrl: str | None = None
    resource: dict[str, Any]
    request: FHIRBundleEntryRequest | None = None


class FHIRBundleRequest(BaseModel):
    """
    FHIR Bundle request specification.

    Represents a FHIR bundle containing one or more resources to be
    created within an encounter context.

    Example:
        {
            "resourceType": "Bundle",
            "type": "transaction",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Condition",
                        "code": {...},
                        ...
                    }
                },
                {
                    "resource": {
                        "resourceType": "Observation",
                        ...
                    }
                }
            ]
        }
    """

    resourceType: str = Field(default="Bundle", description="Must be 'Bundle'")
    type: FHIRBundleType = Field(
        default=FHIRBundleType.transaction,
        description="Bundle type: transaction, batch, or collection",
    )
    entry: list[FHIRBundleEntry] = Field(
        ...,
        min_length=1,
        description="List of bundle entries containing resources",
    )
    id: str | None = Field(
        default=None, description="Optional bundle identifier"
    )
    meta: dict[str, Any] | None = Field(
        default=None, description="Optional metadata"
    )

    class Config:
        extra = "allow"


class FHIRBundleEntryResult(BaseModel):
    """
    Result for a single bundle entry processing.
    """

    success: bool
    resource_type: str | None = None
    fhir_id: str | None = None
    care_id: str | None = None
    errors: list[str] | None = None
    stored_as: str | None = Field(
        default=None,
        description=(
            "Indicates how the resource was stored. 'native' for directly "
            "supported resources, 'questionnaire_response' for resources "
            "stored via questionnaire fallback."
        ),
    )
    questionnaire_slug: str | None = Field(
        default=None,
        description="The questionnaire slug if stored via questionnaire fallback.",
    )


class FHIRBundleResponse(BaseModel):
    """
    Response from FHIR bundle processing.

    Contains the overall success status and individual results
    for each entry in the bundle.
    """

    success: bool = Field(description="Overall success status")
    bundle_type: str | None = Field(description="Type of bundle processed")
    total_entries: int = Field(description="Total number of entries in bundle")
    processed: int = Field(description="Number of successfully processed entries")
    failed: int = Field(description="Number of failed entries")
    results: list[FHIRBundleEntryResult] = Field(
        default_factory=list,
        description="Individual results for each entry",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Bundle-level errors",
    )
    encounter_id: UUID4 | None = Field(
        default=None,
        description="The encounter ID used for processing",
    )


class FHIRBundleProcessRequest(BaseModel):
    """
    Request wrapper for the bundle processing endpoint.

    This wraps the FHIR bundle with additional context needed for processing.
    """

    encounter: UUID4 = Field(
        description="The encounter UUID to associate resources with"
    )
    bundle: FHIRBundleRequest = Field(
        description="The FHIR bundle containing resources to process"
    )
    fail_on_error: bool = Field(
        default=True,
        description=(
            "If true, all changes are rolled back on any error (transaction semantics). "
            "If false, each entry is processed independently (batch semantics)."
        ),
    )
    use_questionnaire_fallback: bool = Field(
        default=True,
        description=(
            "If true, unsupported FHIR resource types will be stored as "
            "questionnaire responses, preserving the data. If false, unsupported "
            "resources will cause an error."
        ),
    )
