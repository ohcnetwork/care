"""
FHIR Bundle Generator Service.

This module provides functionality to generate FHIR bundles from
medical transcription text using AI models.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any

from care.scribe.services.ai_service import (
    AIProvider,
    AIServiceFactory,
    GenerationResult,
)
from care.scribe.validators.bundle_validator import (
    FHIRBundleValidator,
    ValidationResult,
)

logger = logging.getLogger(__name__)


@dataclass
class FHIRGenerationConfig:
    """Configuration for FHIR bundle generation."""

    provider: AIProvider = AIProvider.OPENAI
    model: str = "gpt-4o"
    temperature: float = 0.3  # Lower temperature for more deterministic output
    max_tokens: int = 8192
    api_key: str | None = None
    api_base: str | None = None


@dataclass
class FHIRGenerationResult:
    """Result from FHIR bundle generation."""

    bundle: dict[str, Any] | None
    validation: ValidationResult | None
    raw_response: str | None
    generation_result: GenerationResult | None
    error: str | None = None


class FHIRBundleGenerator:
    """
    Service for generating FHIR bundles from medical transcriptions.

    Uses AI models to extract clinical information from transcribed text
    and structure it as valid FHIR resources.
    """

    # System prompt for FHIR bundle generation
    SYSTEM_PROMPT = """You are a medical AI assistant specialized in converting clinical consultation transcripts into FHIR R4 bundles.

Your task is to analyze medical consultation transcripts and extract relevant clinical information, structuring it as a valid FHIR R4 bundle.

## SUPPORTED FHIR RESOURCE TYPES

You MUST ONLY use the following resource types as our system only supports these:

1. **Condition** - For diagnoses, symptoms, problems, and clinical findings
   - Use for: chief complaints, diagnoses, symptoms, medical problems

2. **Observation** - For vital signs, lab results, clinical measurements, and findings
   - Use for: blood pressure, temperature, heart rate, lab values, physical exam findings

3. **MedicationRequest** - For newly prescribed medications
   - Use for: prescriptions, medication orders given during the consultation

4. **MedicationStatement** - For current/existing medications the patient is taking
   - Use for: medication history, current medications, home medications

5. **AllergyIntolerance** - For allergies and adverse reactions
   - Use for: drug allergies, food allergies, environmental allergies, adverse reactions

6. **Procedure** - For procedures performed, planned, or in patient history
   - Use for: surgical history, procedures done during visit, planned procedures

7. **ServiceRequest** - For tests, investigations, or referrals ordered
   - Use for: lab orders, imaging orders, referrals, diagnostic tests ordered

8. **FamilyMemberHistory** - For family medical history
   - Use for: hereditary conditions, family diseases, genetic history

9. **Immunization** - For vaccination history
   - Use for: vaccines given, immunization records

10. **DiagnosticReport** - For diagnostic test results and reports
    - Use for: lab reports, imaging reports, pathology reports

11. **Encounter** - For visit/encounter details (only if explicitly needed)
    - Use for: encounter type, reason for visit context

## FALLBACK: QuestionnaireResponse

For ANY clinical information that does NOT fit into the above supported resource types, you MUST use **QuestionnaireResponse** to capture it. This includes but is not limited to:

- Social history (smoking, alcohol, occupation, lifestyle)
- Travel history
- Review of systems details
- Patient preferences or goals
- Care plans or instructions
- Follow-up instructions
- Any other narrative clinical information

QuestionnaireResponse format:
{
  "resourceType": "QuestionnaireResponse",
  "status": "completed",
  "item": [
    {
      "linkId": "category-name",
      "text": "Category Display Name",
      "item": [
        {
          "linkId": "item-id",
          "text": "Question or Field Name",
          "answer": [
            {"valueString": "The captured value or information"}
          ]
        }
      ]
    }
  ]
}

Use meaningful linkIds like "social-history", "travel-history", "lifestyle", "follow-up-instructions", etc.

## Guidelines

1. Extract ALL clinically relevant information from the transcript
2. Use ONLY the supported resource types listed above
3. Use QuestionnaireResponse for anything that doesn't fit the supported types
4. Include proper codings using standard systems (SNOMED-CT, ICD-10, LOINC, RxNorm) when possible
5. If exact codes are unknown, provide descriptive text with appropriate coding structure
6. Ensure all resources are properly structured according to FHIR R4 specification
7. Set appropriate status values for each resource

## Output Format

Return ONLY a valid JSON object representing a FHIR Bundle with type "transaction".
Do not include any explanation or markdown formatting.

{
  "resourceType": "Bundle",
  "type": "transaction",
  "entry": [
    {
      "resource": { ... FHIR resource ... },
      "request": {
        "method": "POST",
        "url": "ResourceType"
      }
    }
  ]
}"""

    # User prompt template
    USER_PROMPT_TEMPLATE = """Analyze the following medical consultation transcript and extract all clinical information into a FHIR R4 bundle.

Transcript:
{transcript}

{additional_context}

Generate a FHIR R4 bundle containing all extracted clinical information. Return ONLY the JSON bundle, no additional text."""

    def __init__(self, config: FHIRGenerationConfig | None = None):
        """
        Initialize the FHIR bundle generator.

        Args:
            config: Optional generation configuration
        """
        self.config = config or FHIRGenerationConfig()
        self.validator = FHIRBundleValidator()

    def get_ai_service(self):
        """Get the AI service for generation."""
        return AIServiceFactory.create_from_settings(
            provider=self.config.provider,
            model_name=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            api_key=self.config.api_key,
            api_base=self.config.api_base,
        )

    async def generate(
        self,
        transcript: str,
        additional_context: str | None = None,
        validate: bool = True,
        retry_on_invalid: bool = True,
        max_retries: int = 2,
    ) -> FHIRGenerationResult:
        """
        Generate a FHIR bundle from a medical transcript.

        Args:
            transcript: The medical consultation transcript
            additional_context: Optional additional context (patient info, etc.)
            validate: If True, validate the generated bundle
            retry_on_invalid: If True, retry generation on validation failure
            max_retries: Maximum number of retry attempts

        Returns:
            FHIRGenerationResult containing the bundle and validation info
        """
        context_str = ""
        if additional_context:
            context_str = f"Additional Context:\n{additional_context}"

        user_prompt = self.USER_PROMPT_TEMPLATE.format(
            transcript=transcript,
            additional_context=context_str,
        )

        ai_service = self.get_ai_service()
        attempts = 0
        last_error = None

        while attempts <= max_retries:
            attempts += 1

            try:
                # Generate the bundle
                generation_result = await ai_service.generate_text(
                    prompt=user_prompt,
                    system_prompt=self.SYSTEM_PROMPT,
                    json_mode=True,
                )

                raw_response = generation_result.content

                # Parse the JSON response
                try:
                    bundle = self._parse_json_response(raw_response)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON response: {e}")
                    last_error = f"Invalid JSON in response: {e}"
                    if retry_on_invalid and attempts <= max_retries:
                        user_prompt = self._add_error_context(
                            user_prompt,
                            f"Previous response was not valid JSON: {e}"
                        )
                        continue
                    return FHIRGenerationResult(
                        bundle=None,
                        validation=None,
                        raw_response=raw_response,
                        generation_result=generation_result,
                        error=last_error,
                    )

                # Validate the bundle if requested
                validation_result = None
                if validate:
                    validation_result = self.validator.validate(bundle)

                    if not validation_result.is_valid and retry_on_invalid and attempts <= max_retries:
                        error_summary = self._format_validation_errors(validation_result)
                        logger.warning(f"Generated bundle failed validation: {error_summary}")
                        user_prompt = self._add_error_context(
                            user_prompt,
                            f"Previous bundle was invalid: {error_summary}"
                        )
                        last_error = error_summary
                        continue

                logger.info(
                    f"Successfully generated FHIR bundle with "
                    f"{validation_result.resource_count if validation_result else 'unknown'} resources"
                )

                return FHIRGenerationResult(
                    bundle=bundle,
                    validation=validation_result,
                    raw_response=raw_response,
                    generation_result=generation_result,
                    error=None if (validation_result is None or validation_result.is_valid) else last_error,
                )

            except Exception as e:
                logger.exception(f"Error generating FHIR bundle: {e}")
                last_error = str(e)
                if attempts <= max_retries:
                    continue
                return FHIRGenerationResult(
                    bundle=None,
                    validation=None,
                    raw_response=None,
                    generation_result=None,
                    error=str(e),
                )

        # Should not reach here, but just in case
        return FHIRGenerationResult(
            bundle=None,
            validation=None,
            raw_response=None,
            generation_result=None,
            error=last_error or "Maximum retries exceeded",
        )

    def generate_sync(
        self,
        transcript: str,
        additional_context: str | None = None,
        validate: bool = True,
        retry_on_invalid: bool = True,
        max_retries: int = 2,
    ) -> FHIRGenerationResult:
        """
        Synchronous version of generate.

        Args:
            transcript: The medical consultation transcript
            additional_context: Optional additional context
            validate: If True, validate the generated bundle
            retry_on_invalid: If True, retry generation on validation failure
            max_retries: Maximum number of retry attempts

        Returns:
            FHIRGenerationResult containing the bundle and validation info
        """
        import asyncio

        return asyncio.get_event_loop().run_until_complete(
            self.generate(transcript, additional_context, validate, retry_on_invalid, max_retries)
        )

    def _parse_json_response(self, response: str) -> dict[str, Any]:
        """
        Parse JSON from the AI response.

        Handles potential markdown code blocks and extra whitespace.
        """
        # Remove potential markdown code block formatting
        cleaned = response.strip()

        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]

        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        cleaned = cleaned.strip()

        return json.loads(cleaned)

    def _add_error_context(self, prompt: str, error: str) -> str:
        """Add error context to the prompt for retry."""
        return f"{prompt}\n\nIMPORTANT: {error}\nPlease correct these issues in your response."

    def _format_validation_errors(self, validation: ValidationResult) -> str:
        """Format validation errors for feedback."""
        errors = []
        for error in validation.errors[:5]:  # Limit to first 5 errors
            errors.append(f"- {error.path}: {error.message}")
        return "\n".join(errors)

    @staticmethod
    def get_supported_resource_types() -> list[str]:
        """Return list of FHIR resource types that can be generated."""
        return FHIRBundleValidator.get_supported_resource_types()
