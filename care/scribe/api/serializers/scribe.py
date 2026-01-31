"""
Serializers for the Scribe API.

Handles request validation and response formatting for the scribe endpoints.
"""

from rest_framework import serializers

from care.scribe.services.ai_service import AIProvider
from care.scribe.services.transcription import TranscriptionService


class AIModelParametersSerializer(serializers.Serializer):
    """Serializer for AI model parameters."""

    temperature = serializers.FloatField(
        required=False,
        min_value=0.0,
        max_value=2.0,
        default=0.3,
        help_text="Temperature for text generation (0.0-2.0). Lower values are more deterministic.",
    )
    max_tokens = serializers.IntegerField(
        required=False,
        min_value=100,
        max_value=128000,
        default=8192,
        help_text="Maximum number of tokens to generate.",
    )


class TranscriptionModelSerializer(serializers.Serializer):
    """Serializer for transcription model configuration."""

    provider = serializers.ChoiceField(
        choices=[(p.value, p.value) for p in AIProvider],
        default=AIProvider.OPENAI.value,
        help_text="AI provider for transcription.",
    )
    model = serializers.CharField(
        required=False,
        default="whisper-1",
        help_text="Model to use for transcription.",
    )


class GenerationModelSerializer(serializers.Serializer):
    """Serializer for generation model configuration."""

    provider = serializers.ChoiceField(
        choices=[(p.value, p.value) for p in AIProvider],
        default=AIProvider.OPENAI.value,
        help_text="AI provider for FHIR generation.",
    )
    model = serializers.CharField(
        required=False,
        default="gpt-4o",
        help_text="Model to use for FHIR generation.",
    )
    parameters = AIModelParametersSerializer(
        required=False,
        help_text="Additional model parameters.",
    )


class ScribeMetadataSerializer(serializers.Serializer):
    """Serializer for scribe request metadata."""

    patient_context = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Additional patient context (age, gender, known conditions, etc.)",
    )
    encounter_type = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Type of encounter (e.g., 'outpatient', 'emergency', 'follow-up').",
    )
    specialty = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Medical specialty (e.g., 'cardiology', 'general-medicine').",
    )
    language = serializers.CharField(
        required=False,
        max_length=10,
        help_text="ISO-639-1 language code for audio (e.g., 'en', 'es').",
    )
    custom_instructions = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Custom instructions for the AI model.",
    )


class ScribeRequestSerializer(serializers.Serializer):
    """
    Serializer for scribe API requests.

    Validates the audio file, model configuration, and metadata.
    """

    audio = serializers.FileField(
        help_text="Audio file of the medical consultation.",
    )
    metadata = ScribeMetadataSerializer(
        required=False,
        help_text="Additional metadata for the transcription.",
    )
    transcription_model = TranscriptionModelSerializer(
        required=False,
        help_text="Configuration for the transcription model.",
    )
    generation_model = GenerationModelSerializer(
        required=False,
        help_text="Configuration for the FHIR generation model.",
    )
    validate_bundle = serializers.BooleanField(
        default=True,
        help_text="Whether to validate the generated FHIR bundle.",
    )
    include_transcript = serializers.BooleanField(
        default=True,
        help_text="Whether to include the transcript in the response.",
    )

    def validate_audio(self, value):
        """Validate the audio file."""
        # Check file size (limit to 25MB for Whisper API)
        max_size = 25 * 1024 * 1024  # 25MB
        if value.size > max_size:
            raise serializers.ValidationError(
                f"Audio file too large. Maximum size is 25MB, got {value.size / (1024*1024):.1f}MB"
            )

        # Check file extension
        supported_formats = TranscriptionService.get_supported_audio_formats()
        file_ext = value.name.split(".")[-1].lower() if "." in value.name else ""

        if file_ext not in supported_formats:
            raise serializers.ValidationError(
                f"Unsupported audio format: {file_ext}. "
                f"Supported formats: {', '.join(supported_formats)}"
            )

        return value


class ScribeTranscriptRequestSerializer(serializers.Serializer):
    """
    Serializer for scribe requests with pre-existing transcript.

    Used when the audio has already been transcribed.
    """

    transcript = serializers.CharField(
        help_text="The medical consultation transcript.",
    )
    metadata = ScribeMetadataSerializer(
        required=False,
        help_text="Additional metadata for the generation.",
    )
    generation_model = GenerationModelSerializer(
        required=False,
        help_text="Configuration for the FHIR generation model.",
    )
    validate_bundle = serializers.BooleanField(
        default=True,
        help_text="Whether to validate the generated FHIR bundle.",
    )


class ValidationErrorSerializer(serializers.Serializer):
    """Serializer for validation errors."""

    path = serializers.CharField()
    message = serializers.CharField()
    severity = serializers.CharField()


class ValidationResultSerializer(serializers.Serializer):
    """Serializer for bundle validation results."""

    is_valid = serializers.BooleanField()
    errors = ValidationErrorSerializer(many=True, required=False)
    warnings = ValidationErrorSerializer(many=True, required=False)
    resource_count = serializers.IntegerField()
    resource_types = serializers.ListField(child=serializers.CharField())


class UsageSerializer(serializers.Serializer):
    """Serializer for AI usage information."""

    prompt_tokens = serializers.IntegerField(required=False)
    completion_tokens = serializers.IntegerField(required=False)
    total_tokens = serializers.IntegerField(required=False)


class ScribeResponseSerializer(serializers.Serializer):
    """
    Serializer for scribe API responses.

    Contains the generated FHIR bundle and associated metadata.
    """

    success = serializers.BooleanField(
        help_text="Whether the scribe operation was successful.",
    )
    bundle = serializers.JSONField(
        required=False,
        allow_null=True,
        help_text="The generated FHIR bundle.",
    )
    validation = ValidationResultSerializer(
        required=False,
        allow_null=True,
        help_text="Validation results for the generated bundle.",
    )
    transcript = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="The transcribed text from the audio.",
    )
    transcript_language = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Detected language of the transcript.",
    )
    transcript_duration = serializers.FloatField(
        required=False,
        allow_null=True,
        help_text="Duration of the audio in seconds.",
    )
    usage = UsageSerializer(
        required=False,
        allow_null=True,
        help_text="Token usage information.",
    )
    error = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Error message if the operation failed.",
    )


class SupportedModelsResponseSerializer(serializers.Serializer):
    """Serializer for supported models response."""

    providers = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of supported AI providers.",
    )
    audio_formats = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of supported audio formats.",
    )
    languages = serializers.DictField(
        child=serializers.CharField(),
        help_text="Dictionary of supported language codes and names.",
    )
    fhir_resource_types = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of FHIR resource types that can be generated.",
    )
