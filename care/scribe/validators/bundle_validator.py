"""
FHIR Bundle Validator.

This module provides validation for FHIR bundles to ensure they conform
to the FHIR specification and contain valid resource types.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# Valid FHIR R4 resource types
FHIR_RESOURCE_TYPES = {
    "Account",
    "ActivityDefinition",
    "AdverseEvent",
    "AllergyIntolerance",
    "Appointment",
    "AppointmentResponse",
    "AuditEvent",
    "Basic",
    "Binary",
    "BiologicallyDerivedProduct",
    "BodyStructure",
    "Bundle",
    "CapabilityStatement",
    "CarePlan",
    "CareTeam",
    "CatalogEntry",
    "ChargeItem",
    "ChargeItemDefinition",
    "Claim",
    "ClaimResponse",
    "ClinicalImpression",
    "CodeSystem",
    "Communication",
    "CommunicationRequest",
    "CompartmentDefinition",
    "Composition",
    "ConceptMap",
    "Condition",
    "Consent",
    "Contract",
    "Coverage",
    "CoverageEligibilityRequest",
    "CoverageEligibilityResponse",
    "DetectedIssue",
    "Device",
    "DeviceDefinition",
    "DeviceMetric",
    "DeviceRequest",
    "DeviceUseStatement",
    "DiagnosticReport",
    "DocumentManifest",
    "DocumentReference",
    "EffectEvidenceSynthesis",
    "Encounter",
    "Endpoint",
    "EnrollmentRequest",
    "EnrollmentResponse",
    "EpisodeOfCare",
    "EventDefinition",
    "Evidence",
    "EvidenceVariable",
    "ExampleScenario",
    "ExplanationOfBenefit",
    "FamilyMemberHistory",
    "Flag",
    "Goal",
    "GraphDefinition",
    "Group",
    "GuidanceResponse",
    "HealthcareService",
    "ImagingStudy",
    "Immunization",
    "ImmunizationEvaluation",
    "ImmunizationRecommendation",
    "ImplementationGuide",
    "InsurancePlan",
    "Invoice",
    "Library",
    "Linkage",
    "List",
    "Location",
    "Measure",
    "MeasureReport",
    "Media",
    "Medication",
    "MedicationAdministration",
    "MedicationDispense",
    "MedicationKnowledge",
    "MedicationRequest",
    "MedicationStatement",
    "MedicinalProduct",
    "MedicinalProductAuthorization",
    "MedicinalProductContraindication",
    "MedicinalProductIndication",
    "MedicinalProductIngredient",
    "MedicinalProductInteraction",
    "MedicinalProductManufactured",
    "MedicinalProductPackaged",
    "MedicinalProductPharmaceutical",
    "MedicinalProductUndesirableEffect",
    "MessageDefinition",
    "MessageHeader",
    "MolecularSequence",
    "NamingSystem",
    "NutritionOrder",
    "Observation",
    "ObservationDefinition",
    "OperationDefinition",
    "OperationOutcome",
    "Organization",
    "OrganizationAffiliation",
    "Parameters",
    "Patient",
    "PaymentNotice",
    "PaymentReconciliation",
    "Person",
    "PlanDefinition",
    "Practitioner",
    "PractitionerRole",
    "Procedure",
    "Provenance",
    "Questionnaire",
    "QuestionnaireResponse",
    "RelatedPerson",
    "RequestGroup",
    "ResearchDefinition",
    "ResearchElementDefinition",
    "ResearchStudy",
    "ResearchSubject",
    "RiskAssessment",
    "RiskEvidenceSynthesis",
    "Schedule",
    "SearchParameter",
    "ServiceRequest",
    "Slot",
    "Specimen",
    "SpecimenDefinition",
    "StructureDefinition",
    "StructureMap",
    "Subscription",
    "Substance",
    "SubstanceNucleicAcid",
    "SubstancePolymer",
    "SubstanceProtein",
    "SubstanceReferenceInformation",
    "SubstanceSourceMaterial",
    "SubstanceSpecification",
    "SupplyDelivery",
    "SupplyRequest",
    "Task",
    "TerminologyCapabilities",
    "TestReport",
    "TestScript",
    "ValueSet",
    "VerificationResult",
    "VisionPrescription",
}

# Valid FHIR bundle types
FHIR_BUNDLE_TYPES = {
    "document",
    "message",
    "transaction",
    "transaction-response",
    "batch",
    "batch-response",
    "history",
    "searchset",
    "collection",
}


@dataclass
class ValidationError:
    """Represents a single validation error."""

    path: str
    message: str
    severity: str = "error"  # error, warning, info


@dataclass
class ValidationResult:
    """Result of FHIR bundle validation."""

    is_valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)
    resource_count: int = 0
    resource_types: list[str] = field(default_factory=list)

    def add_error(self, path: str, message: str) -> None:
        """Add an error to the validation result."""
        self.errors.append(ValidationError(path=path, message=message, severity="error"))

    def add_warning(self, path: str, message: str) -> None:
        """Add a warning to the validation result."""
        self.warnings.append(ValidationError(path=path, message=message, severity="warning"))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "is_valid": self.is_valid,
            "errors": [
                {"path": e.path, "message": e.message, "severity": e.severity}
                for e in self.errors
            ],
            "warnings": [
                {"path": w.path, "message": w.message, "severity": w.severity}
                for w in self.warnings
            ],
            "resource_count": self.resource_count,
            "resource_types": self.resource_types,
        }


class FHIRBundleValidator:
    """
    Validator for FHIR bundles.

    Validates bundle structure, resource types, and basic FHIR compliance.
    This is not a full FHIR profile validator but ensures basic structural
    correctness for the bundle processing pipeline.
    """

    # Supported resource types for the scribe pipeline
    # These are the clinical resource types we can process
    SUPPORTED_RESOURCE_TYPES = {
        "AllergyIntolerance",
        "Condition",
        "DiagnosticReport",
        "Encounter",
        "FamilyMemberHistory",
        "Immunization",
        "MedicationRequest",
        "MedicationStatement",
        "Observation",
        "Procedure",
        "QuestionnaireResponse",  # Fallback for any data not fitting other types
        "ServiceRequest",
    }

    def __init__(
        self,
        strict_mode: bool = False,
        allowed_resource_types: set[str] | None = None,
    ):
        """
        Initialize the validator.

        Args:
            strict_mode: If True, treat warnings as errors
            allowed_resource_types: Optional set of allowed resource types.
                                   If None, all FHIR resource types are allowed.
        """
        self.strict_mode = strict_mode
        self.allowed_resource_types = allowed_resource_types

    def validate(self, bundle: dict[str, Any]) -> ValidationResult:
        """
        Validate a FHIR bundle.

        Args:
            bundle: The bundle dictionary to validate

        Returns:
            ValidationResult containing validation status and any errors
        """
        result = ValidationResult(is_valid=True)
        resource_types = []

        # Check if it's a valid dictionary
        if not isinstance(bundle, dict):
            result.add_error("", "Bundle must be a JSON object")
            result.is_valid = False
            return result

        # Validate resourceType
        resource_type = bundle.get("resourceType")
        if resource_type != "Bundle":
            result.add_error(
                "resourceType",
                f"Expected resourceType 'Bundle', got '{resource_type}'"
            )
            result.is_valid = False
            return result

        # Validate bundle type
        bundle_type = bundle.get("type")
        if not bundle_type:
            result.add_error("type", "Bundle type is required")
            result.is_valid = False
        elif bundle_type not in FHIR_BUNDLE_TYPES:
            result.add_error(
                "type",
                f"Invalid bundle type '{bundle_type}'. Valid types: {', '.join(FHIR_BUNDLE_TYPES)}"
            )
            result.is_valid = False

        # Validate entries
        entries = bundle.get("entry", [])
        if not isinstance(entries, list):
            result.add_error("entry", "Bundle entry must be an array")
            result.is_valid = False
            return result

        if len(entries) == 0:
            result.add_warning("entry", "Bundle contains no entries")

        # Validate each entry
        for idx, entry in enumerate(entries):
            entry_path = f"entry[{idx}]"
            entry_result = self._validate_entry(entry, entry_path)

            if entry_result.errors:
                result.errors.extend(entry_result.errors)
                result.is_valid = False

            if entry_result.warnings:
                result.warnings.extend(entry_result.warnings)
                if self.strict_mode:
                    result.is_valid = False

            if entry_result.resource_types:
                resource_types.extend(entry_result.resource_types)

        result.resource_count = len(entries)
        result.resource_types = list(set(resource_types))

        return result

    def _validate_entry(self, entry: dict[str, Any], path: str) -> ValidationResult:
        """Validate a single bundle entry."""
        result = ValidationResult(is_valid=True)

        if not isinstance(entry, dict):
            result.add_error(path, "Entry must be a JSON object")
            return result

        # Check for resource
        resource = entry.get("resource")
        if resource is None:
            result.add_error(f"{path}.resource", "Entry must contain a resource")
            return result

        if not isinstance(resource, dict):
            result.add_error(f"{path}.resource", "Resource must be a JSON object")
            return result

        # Validate resource type
        resource_type = resource.get("resourceType")
        if not resource_type:
            result.add_error(
                f"{path}.resource.resourceType",
                "Resource must have a resourceType"
            )
        elif resource_type not in FHIR_RESOURCE_TYPES:
            result.add_error(
                f"{path}.resource.resourceType",
                f"Invalid resource type: {resource_type}"
            )
        else:
            result.resource_types.append(resource_type)

            # Check if resource type is in allowed list
            if self.allowed_resource_types and resource_type not in self.allowed_resource_types:
                result.add_warning(
                    f"{path}.resource.resourceType",
                    f"Resource type '{resource_type}' is not in the list of supported types"
                )

        # Validate fullUrl if present
        full_url = entry.get("fullUrl")
        if full_url is not None and not isinstance(full_url, str):
            result.add_error(f"{path}.fullUrl", "fullUrl must be a string")

        # Validate request if present
        request = entry.get("request")
        if request is not None:
            self._validate_request(request, f"{path}.request", result)

        return result

    def _validate_request(
        self, request: dict[str, Any], path: str, result: ValidationResult
    ) -> None:
        """Validate the request element of a bundle entry."""
        if not isinstance(request, dict):
            result.add_error(path, "Request must be a JSON object")
            return

        # Validate method
        method = request.get("method")
        if method is None:
            result.add_error(f"{path}.method", "Request method is required")
        elif method not in {"GET", "HEAD", "POST", "PUT", "DELETE", "PATCH"}:
            result.add_error(f"{path}.method", f"Invalid request method: {method}")

        # Validate url
        url = request.get("url")
        if url is None:
            result.add_error(f"{path}.url", "Request URL is required")
        elif not isinstance(url, str):
            result.add_error(f"{path}.url", "Request URL must be a string")

    def validate_resource(self, resource: dict[str, Any]) -> ValidationResult:
        """
        Validate a single FHIR resource.

        Args:
            resource: The resource dictionary to validate

        Returns:
            ValidationResult containing validation status and any errors
        """
        result = ValidationResult(is_valid=True)

        if not isinstance(resource, dict):
            result.add_error("", "Resource must be a JSON object")
            result.is_valid = False
            return result

        resource_type = resource.get("resourceType")
        if not resource_type:
            result.add_error("resourceType", "Resource must have a resourceType")
            result.is_valid = False
        elif resource_type not in FHIR_RESOURCE_TYPES:
            result.add_error(
                "resourceType",
                f"Invalid resource type: {resource_type}"
            )
            result.is_valid = False
        else:
            result.resource_types.append(resource_type)
            result.resource_count = 1

        return result

    @classmethod
    def is_valid_bundle(cls, data: dict[str, Any]) -> bool:
        """
        Quick check if data represents a valid FHIR bundle structure.

        Args:
            data: Dictionary to check

        Returns:
            True if it has the basic structure of a FHIR bundle
        """
        if not isinstance(data, dict):
            return False

        if data.get("resourceType") != "Bundle":
            return False

        if data.get("type") not in FHIR_BUNDLE_TYPES:
            return False

        entries = data.get("entry", [])
        if not isinstance(entries, list):
            return False

        return True

    @classmethod
    def get_supported_resource_types(cls) -> list[str]:
        """Return list of resource types supported by the scribe pipeline."""
        return sorted(cls.SUPPORTED_RESOURCE_TYPES)
