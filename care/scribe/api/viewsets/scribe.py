"""
Scribe API ViewSet.

Provides endpoints for AI-powered medical transcription and FHIR bundle generation.
"""

import logging

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from care.scribe.api.serializers.scribe import (
    ScribeRequestSerializer,
    ScribeResponseSerializer,
    ScribeTranscriptRequestSerializer,
    SupportedModelsResponseSerializer,
)
from care.scribe.services.ai_service import AIProvider, AIServiceFactory
from care.scribe.services.fhir_generator import (
    FHIRBundleGenerator,
    FHIRGenerationConfig,
)
from care.scribe.services.transcription import TranscriptionConfig, TranscriptionService
from care.scribe.validators.bundle_validator import FHIRBundleValidator

logger = logging.getLogger(__name__)


class ScribeViewSet(ViewSet):
    """
    ViewSet for AI-powered medical scribe functionality.

    Provides endpoints for:
    - Transcribing audio recordings and generating FHIR bundles
    - Generating FHIR bundles from existing transcripts
    - Listing supported models and configurations

    The scribe accepts audio recordings of medical consultations and uses
    AI models to:
    1. Transcribe the audio to text
    2. Extract clinical information from the transcript
    3. Generate a validated FHIR R4 bundle

    Authorization:
    - Requires authenticated user

    Example Usage:
        POST /api/v1/scribe/process/
        Content-Type: multipart/form-data

        audio: <audio file>
        metadata: {"patient_context": "45 year old male", "specialty": "cardiology"}
        generation_model: {"provider": "openai", "model": "gpt-4o"}
    """

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(
        summary="Get scribe capabilities",
        description="Returns supported AI providers, audio formats, languages, and FHIR resource types.",
        responses={200: SupportedModelsResponseSerializer},
    )
    def list(self, request, *args, **kwargs):
        """
        List supported scribe capabilities.

        Returns information about:
        - Supported AI providers
        - Supported audio formats
        - Supported languages
        - FHIR resource types that can be generated
        """
        data = {
            "providers": AIServiceFactory.get_supported_providers(),
            "audio_formats": TranscriptionService.get_supported_audio_formats(),
            "languages": TranscriptionService.get_supported_languages(),
            "fhir_resource_types": FHIRBundleValidator.get_supported_resource_types(),
        }

        serializer = SupportedModelsResponseSerializer(data)
        return Response(serializer.data)

    @extend_schema(
        summary="Process audio and generate FHIR bundle",
        description=(
            "Accepts an audio recording of a medical consultation, transcribes it "
            "using AI, extracts clinical information, and generates a validated "
            "FHIR R4 bundle containing the extracted data."
        ),
        request=ScribeRequestSerializer,
        responses={
            200: ScribeResponseSerializer,
            400: OpenApiResponse(description="Invalid request"),
            500: OpenApiResponse(description="Processing error"),
        },
    )
    @action(detail=False, methods=["POST"], parser_classes=[MultiPartParser, FormParser])
    def process(self, request, *args, **kwargs):
        """
        Process an audio recording and generate a FHIR bundle.

        This endpoint:
        1. Validates the request and audio file
        2. Transcribes the audio using the specified AI model
        3. Generates a FHIR bundle from the transcript
        4. Validates the generated bundle
        5. Returns the bundle with validation results

        Request Parameters:
            audio: Audio file (multipart form data)
            metadata: Optional metadata (JSON)
            transcription_model: Transcription model config (JSON)
            generation_model: Generation model config (JSON)
            validate_bundle: Whether to validate the bundle (bool)
            include_transcript: Whether to include transcript in response (bool)

        Returns:
            JSON response with FHIR bundle and processing metadata
        """
        # Parse JSON fields from form data
        request_data = self._parse_multipart_request(request)

        serializer = ScribeRequestSerializer(data=request_data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "error": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        validated_data = serializer.validated_data

        try:
            # Step 1: Transcribe the audio
            transcription_result = self._transcribe_audio(validated_data)

            # Step 2: Generate FHIR bundle from transcript
            generation_result = self._generate_fhir_bundle(
                transcript=transcription_result.text,
                validated_data=validated_data,
            )

            # Build response
            response_data = {
                "success": generation_result.bundle is not None and (
                    generation_result.validation is None or
                    generation_result.validation.is_valid
                ),
                "bundle": generation_result.bundle,
                "error": generation_result.error,
            }

            # Include validation results
            if generation_result.validation:
                response_data["validation"] = generation_result.validation.to_dict()

            # Include transcript if requested
            if validated_data.get("include_transcript", True):
                response_data["transcript"] = transcription_result.text
                response_data["transcript_language"] = transcription_result.language
                response_data["transcript_duration"] = transcription_result.duration

            # Include usage info
            if generation_result.generation_result and generation_result.generation_result.usage:
                response_data["usage"] = generation_result.generation_result.usage

            response_serializer = ScribeResponseSerializer(data=response_data)
            response_serializer.is_valid(raise_exception=True)

            return Response(
                response_serializer.data,
                status=status.HTTP_200_OK if response_data["success"] else status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            logger.exception(f"Error processing scribe request: {e}")
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        summary="Generate FHIR bundle from transcript",
        description=(
            "Accepts a pre-existing transcript of a medical consultation and "
            "generates a validated FHIR R4 bundle containing extracted clinical data."
        ),
        request=ScribeTranscriptRequestSerializer,
        responses={
            200: ScribeResponseSerializer,
            400: OpenApiResponse(description="Invalid request"),
            500: OpenApiResponse(description="Processing error"),
        },
    )
    @action(detail=False, methods=["POST"])
    def generate(self, request, *args, **kwargs):
        """
        Generate a FHIR bundle from an existing transcript.

        This endpoint is useful when audio has already been transcribed
        or when working with text-based consultations.

        Request Parameters:
            transcript: The consultation transcript (string)
            metadata: Optional metadata (JSON)
            generation_model: Generation model config (JSON)
            validate_bundle: Whether to validate the bundle (bool)

        Returns:
            JSON response with FHIR bundle and validation results
        """
        serializer = ScribeTranscriptRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "error": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        validated_data = serializer.validated_data

        try:
            # Generate FHIR bundle from transcript
            generation_result = self._generate_fhir_bundle(
                transcript=validated_data["transcript"],
                validated_data=validated_data,
            )

            # Build response
            response_data = {
                "success": generation_result.bundle is not None and (
                    generation_result.validation is None or
                    generation_result.validation.is_valid
                ),
                "bundle": generation_result.bundle,
                "error": generation_result.error,
            }

            # Include validation results
            if generation_result.validation:
                response_data["validation"] = generation_result.validation.to_dict()

            # Include usage info
            if generation_result.generation_result and generation_result.generation_result.usage:
                response_data["usage"] = generation_result.generation_result.usage

            response_serializer = ScribeResponseSerializer(data=response_data)
            response_serializer.is_valid(raise_exception=True)

            return Response(
                response_serializer.data,
                status=status.HTTP_200_OK if response_data["success"] else status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            logger.exception(f"Error generating FHIR bundle: {e}")
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        summary="Validate a FHIR bundle",
        description="Validates an existing FHIR bundle against the FHIR R4 specification.",
        request={"application/json": {"type": "object"}},
        responses={200: dict},
    )
    @action(detail=False, methods=["POST"])
    def validate(self, request, *args, **kwargs):
        """
        Validate a FHIR bundle.

        Accepts a FHIR bundle and returns validation results without
        performing any AI processing.

        Request Body:
            A FHIR bundle JSON object

        Returns:
            Validation results including errors and warnings
        """
        if not request.data:
            return Response(
                {"error": "Request body must contain a FHIR bundle"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        validator = FHIRBundleValidator()
        result = validator.validate(request.data)

        return Response(result.to_dict())

    def _parse_multipart_request(self, request) -> dict:
        """Parse multipart form data with JSON fields."""
        import json

        data = {
            "audio": request.FILES.get("audio"),
        }

        # Parse JSON fields
        for field in ["metadata", "transcription_model", "generation_model"]:
            if field in request.data:
                value = request.data.get(field)
                if isinstance(value, str):
                    try:
                        data[field] = json.loads(value)
                    except json.JSONDecodeError:
                        data[field] = value
                else:
                    data[field] = value

        # Parse boolean fields
        for field in ["validate_bundle", "include_transcript"]:
            if field in request.data:
                value = request.data.get(field)
                if isinstance(value, str):
                    data[field] = value.lower() in ("true", "1", "yes")
                else:
                    data[field] = value

        return data

    def _transcribe_audio(self, validated_data: dict):
        """Transcribe audio using the configured model."""
        import asyncio
        import io

        # Get transcription config
        transcription_config_data = validated_data.get("transcription_model", {})
        metadata = validated_data.get("metadata", {})

        config = TranscriptionConfig(
            provider=AIProvider(transcription_config_data.get("provider", "openai")),
            model=transcription_config_data.get("model", "whisper-1"),
            language=metadata.get("language"),
        )

        service = TranscriptionService(config=config)

        # Get the audio file and convert to proper format for OpenAI
        uploaded_file = validated_data["audio"]

        # Read the file content and create a proper file-like object
        # OpenAI expects (filename, file_content, content_type) tuple or bytes
        file_content = uploaded_file.read()
        audio_file = io.BytesIO(file_content)
        audio_file.name = uploaded_file.name  # OpenAI uses this for format detection

        # Run transcription
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                service.transcribe(
                    audio_file=audio_file,
                    language=metadata.get("language"),
                )
            )
        finally:
            loop.close()

        return result

    def _generate_fhir_bundle(self, transcript: str, validated_data: dict):
        """Generate FHIR bundle from transcript."""
        import asyncio

        # Get generation config
        generation_config_data = validated_data.get("generation_model", {})
        parameters = generation_config_data.get("parameters", {})
        metadata = validated_data.get("metadata", {})

        config = FHIRGenerationConfig(
            provider=AIProvider(generation_config_data.get("provider", "openai")),
            model=generation_config_data.get("model", "gpt-4o"),
            temperature=parameters.get("temperature", 0.3),
            max_tokens=parameters.get("max_tokens", 8192),
        )

        generator = FHIRBundleGenerator(config=config)

        # Build additional context from metadata
        context_parts = []
        if metadata.get("patient_context"):
            context_parts.append(f"Patient Information: {metadata['patient_context']}")
        if metadata.get("encounter_type"):
            context_parts.append(f"Encounter Type: {metadata['encounter_type']}")
        if metadata.get("specialty"):
            context_parts.append(f"Medical Specialty: {metadata['specialty']}")
        if metadata.get("custom_instructions"):
            context_parts.append(f"Special Instructions: {metadata['custom_instructions']}")

        additional_context = "\n".join(context_parts) if context_parts else None

        # Run generation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                generator.generate(
                    transcript=transcript,
                    additional_context=additional_context,
                    validate=validated_data.get("validate_bundle", True),
                )
            )
        finally:
            loop.close()

        return result
