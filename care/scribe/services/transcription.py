"""
Transcription Service.

This module provides audio transcription functionality using the AI service layer.
"""

import logging
from dataclasses import dataclass
from typing import BinaryIO

from care.scribe.services.ai_service import (
    AIModelConfig,
    AIProvider,
    AIServiceFactory,
    TranscriptionResult,
)

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionConfig:
    """Configuration for transcription."""

    provider: AIProvider = AIProvider.OPENAI
    model: str = "whisper-1"
    language: str | None = None
    prompt: str | None = None
    api_key: str | None = None
    api_base: str | None = None


class TranscriptionService:
    """
    Service for transcribing audio recordings.

    Supports multiple AI providers and handles audio processing.
    """

    # Default medical transcription prompt to improve accuracy
    DEFAULT_MEDICAL_PROMPT = (
        "This is a medical consultation transcript. "
        "The audio contains a conversation between a healthcare provider and patient "
        "discussing symptoms, medical history, diagnoses, and treatment plans. "
        "Medical terminology and drug names should be transcribed accurately."
    )

    def __init__(self, config: TranscriptionConfig | None = None):
        """
        Initialize the transcription service.

        Args:
            config: Optional transcription configuration
        """
        self.config = config or TranscriptionConfig()

    def get_ai_service(self):
        """Get the AI service for transcription."""
        return AIServiceFactory.create_from_settings(
            provider=self.config.provider,
            model_name=self.config.model,
            api_key=self.config.api_key,
            api_base=self.config.api_base,
            additional_params={
                "transcription_model": self.config.model,
            },
        )

    async def transcribe(
        self,
        audio_file: BinaryIO,
        language: str | None = None,
        prompt: str | None = None,
        use_medical_prompt: bool = True,
    ) -> TranscriptionResult:
        """
        Transcribe audio to text.

        Args:
            audio_file: Binary file-like object containing audio data
            language: Optional ISO-639-1 language code (e.g., 'en', 'es')
            prompt: Optional custom prompt to guide transcription
            use_medical_prompt: If True and no prompt provided, use medical context prompt

        Returns:
            TranscriptionResult with transcribed text and metadata
        """
        # Determine prompt to use
        if prompt is None and use_medical_prompt:
            prompt = self.DEFAULT_MEDICAL_PROMPT

        effective_language = language or self.config.language

        try:
            ai_service = self.get_ai_service()
            result = await ai_service.transcribe_audio(
                audio_file=audio_file,
                language=effective_language,
                prompt=prompt,
            )

            logger.info(
                f"Successfully transcribed audio: {len(result.text)} characters, "
                f"language: {result.language}, duration: {result.duration}s"
            )

            return result

        except Exception as e:
            logger.exception(f"Error during transcription: {e}")
            raise

    def transcribe_sync(
        self,
        audio_file: BinaryIO,
        language: str | None = None,
        prompt: str | None = None,
        use_medical_prompt: bool = True,
    ) -> TranscriptionResult:
        """
        Synchronous version of transcribe.

        Args:
            audio_file: Binary file-like object containing audio data
            language: Optional ISO-639-1 language code
            prompt: Optional custom prompt
            use_medical_prompt: If True and no prompt provided, use medical context prompt

        Returns:
            TranscriptionResult with transcribed text and metadata
        """
        import asyncio

        return asyncio.get_event_loop().run_until_complete(
            self.transcribe(audio_file, language, prompt, use_medical_prompt)
        )

    @staticmethod
    def get_supported_audio_formats() -> list[str]:
        """Return list of supported audio formats."""
        return [
            "flac",
            "m4a",
            "mp3",
            "mp4",
            "mpeg",
            "mpga",
            "oga",
            "ogg",
            "wav",
            "webm",
        ]

    @staticmethod
    def get_supported_languages() -> dict[str, str]:
        """Return dictionary of supported language codes and names."""
        # Subset of languages supported by Whisper
        return {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "nl": "Dutch",
            "pl": "Polish",
            "ru": "Russian",
            "ja": "Japanese",
            "ko": "Korean",
            "zh": "Chinese",
            "ar": "Arabic",
            "hi": "Hindi",
            "bn": "Bengali",
            "ta": "Tamil",
            "te": "Telugu",
            "mr": "Marathi",
            "gu": "Gujarati",
            "kn": "Kannada",
            "ml": "Malayalam",
            "pa": "Punjabi",
            "ur": "Urdu",
        }
