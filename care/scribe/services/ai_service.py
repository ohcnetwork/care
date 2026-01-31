"""
Abstract AI Service layer for multiple AI providers.

This module provides an abstract interface for interacting with various AI
providers (OpenAI, Azure OpenAI, Anthropic, etc.) for both transcription
and text generation tasks.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, BinaryIO

from django.conf import settings

logger = logging.getLogger(__name__)


class AIProvider(str, Enum):
    """Supported AI providers."""

    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


@dataclass
class AIModelConfig:
    """Configuration for an AI model."""

    provider: AIProvider
    model_name: str
    api_key: str | None = None
    api_base: str | None = None
    api_version: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4096
    additional_params: dict[str, Any] = field(default_factory=dict)


@dataclass
class TranscriptionResult:
    """Result from audio transcription."""

    text: str
    language: str | None = None
    duration: float | None = None
    segments: list[dict[str, Any]] | None = None
    raw_response: dict[str, Any] | None = None


@dataclass
class GenerationResult:
    """Result from text generation."""

    content: str
    finish_reason: str | None = None
    usage: dict[str, int] | None = None
    raw_response: dict[str, Any] | None = None


class AIService(ABC):
    """
    Abstract base class for AI services.

    Subclasses implement provider-specific logic for transcription
    and text generation.
    """

    def __init__(self, config: AIModelConfig):
        self.config = config

    @abstractmethod
    async def transcribe_audio(
        self,
        audio_file: BinaryIO,
        language: str | None = None,
        prompt: str | None = None,
    ) -> TranscriptionResult:
        """
        Transcribe audio to text.

        Args:
            audio_file: Binary file-like object containing audio data
            language: Optional ISO-639-1 language code
            prompt: Optional prompt to guide transcription

        Returns:
            TranscriptionResult with transcribed text and metadata
        """
        pass

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        json_mode: bool = False,
    ) -> GenerationResult:
        """
        Generate text using the AI model.

        Args:
            prompt: The user prompt/input
            system_prompt: Optional system prompt for context
            json_mode: If True, request JSON-formatted output

        Returns:
            GenerationResult with generated content
        """
        pass

    def transcribe_audio_sync(
        self,
        audio_file: BinaryIO,
        language: str | None = None,
        prompt: str | None = None,
    ) -> TranscriptionResult:
        """Synchronous wrapper for transcribe_audio."""
        import asyncio

        return asyncio.get_event_loop().run_until_complete(
            self.transcribe_audio(audio_file, language, prompt)
        )

    def generate_text_sync(
        self,
        prompt: str,
        system_prompt: str | None = None,
        json_mode: bool = False,
    ) -> GenerationResult:
        """Synchronous wrapper for generate_text."""
        import asyncio

        return asyncio.get_event_loop().run_until_complete(
            self.generate_text(prompt, system_prompt, json_mode)
        )


class OpenAIService(AIService):
    """AI service implementation for OpenAI and compatible APIs."""

    def __init__(self, config: AIModelConfig):
        super().__init__(config)
        self._client = None
        self._async_client = None

    def _get_client(self):
        """Get or create the synchronous OpenAI client."""
        if self._client is None:
            from openai import OpenAI

            kwargs = {}
            if self.config.api_key:
                kwargs["api_key"] = self.config.api_key
            if self.config.api_base:
                kwargs["base_url"] = self.config.api_base

            self._client = OpenAI(**kwargs)
        return self._client

    def _get_async_client(self):
        """Get or create the async OpenAI client."""
        if self._async_client is None:
            from openai import AsyncOpenAI

            kwargs = {}
            if self.config.api_key:
                kwargs["api_key"] = self.config.api_key
            if self.config.api_base:
                kwargs["base_url"] = self.config.api_base

            self._async_client = AsyncOpenAI(**kwargs)
        return self._async_client

    async def transcribe_audio(
        self,
        audio_file: BinaryIO,
        language: str | None = None,
        prompt: str | None = None,
    ) -> TranscriptionResult:
        """Transcribe audio using OpenAI's Whisper API."""
        client = self._get_async_client()

        kwargs = {
            "model": self.config.additional_params.get(
                "transcription_model", "whisper-1"
            ),
            "file": audio_file,
            "response_format": "verbose_json",
        }

        if language:
            kwargs["language"] = language
        if prompt:
            kwargs["prompt"] = prompt

        try:
            response = await client.audio.transcriptions.create(**kwargs)

            return TranscriptionResult(
                text=response.text,
                language=getattr(response, "language", None),
                duration=getattr(response, "duration", None),
                segments=getattr(response, "segments", None),
                raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
            )
        except Exception as e:
            logger.exception(f"Error transcribing audio with OpenAI: {e}")
            raise

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        json_mode: bool = False,
    ) -> GenerationResult:
        """Generate text using OpenAI's chat completion API."""
        client = self._get_async_client()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs = {
            "model": self.config.model_name,
            "messages": messages,
            "temperature": self.config.temperature,
            # Use max_completion_tokens for newer models (GPT-4o, GPT-4.5, etc.)
            "max_completion_tokens": self.config.max_tokens,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        # Add any additional parameters
        kwargs.update(self.config.additional_params.get("generation_params", {}))

        try:
            response = await client.chat.completions.create(**kwargs)

            choice = response.choices[0]
            return GenerationResult(
                content=choice.message.content,
                finish_reason=choice.finish_reason,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                } if response.usage else None,
                raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
            )
        except Exception as e:
            logger.exception(f"Error generating text with OpenAI: {e}")
            raise


class AzureOpenAIService(AIService):
    """AI service implementation for Azure OpenAI."""

    def __init__(self, config: AIModelConfig):
        super().__init__(config)
        self._client = None
        self._async_client = None

    def _get_async_client(self):
        """Get or create the async Azure OpenAI client."""
        if self._async_client is None:
            from openai import AsyncAzureOpenAI

            self._async_client = AsyncAzureOpenAI(
                api_key=self.config.api_key,
                api_version=self.config.api_version or "2024-02-15-preview",
                azure_endpoint=self.config.api_base,
            )
        return self._async_client

    async def transcribe_audio(
        self,
        audio_file: BinaryIO,
        language: str | None = None,
        prompt: str | None = None,
    ) -> TranscriptionResult:
        """Transcribe audio using Azure OpenAI's Whisper deployment."""
        client = self._get_async_client()

        deployment_name = self.config.additional_params.get(
            "transcription_deployment", "whisper"
        )

        kwargs = {
            "model": deployment_name,
            "file": audio_file,
            "response_format": "verbose_json",
        }

        if language:
            kwargs["language"] = language
        if prompt:
            kwargs["prompt"] = prompt

        try:
            response = await client.audio.transcriptions.create(**kwargs)

            return TranscriptionResult(
                text=response.text,
                language=getattr(response, "language", None),
                duration=getattr(response, "duration", None),
                segments=getattr(response, "segments", None),
                raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
            )
        except Exception as e:
            logger.exception(f"Error transcribing audio with Azure OpenAI: {e}")
            raise

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        json_mode: bool = False,
    ) -> GenerationResult:
        """Generate text using Azure OpenAI's chat completion API."""
        client = self._get_async_client()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs = {
            "model": self.config.model_name,  # This is the deployment name in Azure
            "messages": messages,
            "temperature": self.config.temperature,
            # Use max_completion_tokens for newer models
            "max_completion_tokens": self.config.max_tokens,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = await client.chat.completions.create(**kwargs)

            choice = response.choices[0]
            return GenerationResult(
                content=choice.message.content,
                finish_reason=choice.finish_reason,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                } if response.usage else None,
                raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
            )
        except Exception as e:
            logger.exception(f"Error generating text with Azure OpenAI: {e}")
            raise


class AnthropicService(AIService):
    """AI service implementation for Anthropic Claude."""

    def __init__(self, config: AIModelConfig):
        super().__init__(config)
        self._async_client = None

    def _get_async_client(self):
        """Get or create the async Anthropic client."""
        if self._async_client is None:
            from anthropic import AsyncAnthropic

            self._async_client = AsyncAnthropic(api_key=self.config.api_key)
        return self._async_client

    async def transcribe_audio(
        self,
        audio_file: BinaryIO,
        language: str | None = None,
        prompt: str | None = None,
    ) -> TranscriptionResult:
        """
        Anthropic doesn't have native audio transcription.
        This would need to be handled by a different service.
        """
        raise NotImplementedError(
            "Anthropic does not support audio transcription. "
            "Use a transcription-capable provider like OpenAI."
        )

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        json_mode: bool = False,
    ) -> GenerationResult:
        """Generate text using Anthropic's message API."""
        client = self._get_async_client()

        kwargs = {
            "model": self.config.model_name,
            "max_tokens": self.config.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        # Note: Anthropic doesn't have a native JSON mode like OpenAI
        # but we can request JSON in the prompt

        try:
            response = await client.messages.create(**kwargs)

            content = ""
            for block in response.content:
                if block.type == "text":
                    content += block.text

            return GenerationResult(
                content=content,
                finish_reason=response.stop_reason,
                usage={
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                } if response.usage else None,
                raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
            )
        except Exception as e:
            logger.exception(f"Error generating text with Anthropic: {e}")
            raise


class GoogleAIService(AIService):
    """AI service implementation for Google's Generative AI (Gemini)."""

    def __init__(self, config: AIModelConfig):
        super().__init__(config)
        self._model = None

    def _get_model(self):
        """Get or create the Google Generative AI model."""
        if self._model is None:
            import google.generativeai as genai

            genai.configure(api_key=self.config.api_key)
            self._model = genai.GenerativeModel(self.config.model_name)
        return self._model

    async def transcribe_audio(
        self,
        audio_file: BinaryIO,
        language: str | None = None,
        prompt: str | None = None,
    ) -> TranscriptionResult:
        """
        Google Gemini can process audio but requires different handling.
        For now, we'll raise NotImplementedError.
        """
        raise NotImplementedError(
            "Google AI audio transcription is not yet implemented. "
            "Use OpenAI for transcription."
        )

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        json_mode: bool = False,
    ) -> GenerationResult:
        """Generate text using Google's Generative AI."""
        model = self._get_model()

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        generation_config = {
            "temperature": self.config.temperature,
            "max_output_tokens": self.config.max_tokens,
        }

        if json_mode:
            generation_config["response_mime_type"] = "application/json"

        try:
            response = await model.generate_content_async(
                full_prompt,
                generation_config=generation_config,
            )

            return GenerationResult(
                content=response.text,
                finish_reason=str(response.candidates[0].finish_reason) if response.candidates else None,
                usage=None,  # Google doesn't provide token usage in the same way
                raw_response=None,
            )
        except Exception as e:
            logger.exception(f"Error generating text with Google AI: {e}")
            raise


class AIServiceFactory:
    """Factory for creating AI service instances."""

    _providers: dict[AIProvider, type[AIService]] = {
        AIProvider.OPENAI: OpenAIService,
        AIProvider.AZURE_OPENAI: AzureOpenAIService,
        AIProvider.ANTHROPIC: AnthropicService,
        AIProvider.GOOGLE: GoogleAIService,
    }

    @classmethod
    def create(cls, config: AIModelConfig) -> AIService:
        """
        Create an AI service instance based on the configuration.

        Args:
            config: AI model configuration

        Returns:
            Configured AIService instance

        Raises:
            ValueError: If the provider is not supported
        """
        service_class = cls._providers.get(config.provider)
        if service_class is None:
            raise ValueError(f"Unsupported AI provider: {config.provider}")

        return service_class(config)

    @classmethod
    def create_from_settings(
        cls,
        provider: str | AIProvider,
        model_name: str | None = None,
        **override_params,
    ) -> AIService:
        """
        Create an AI service using Django settings with optional overrides.

        Args:
            provider: The AI provider to use
            model_name: Optional model name override
            **override_params: Additional parameters to override defaults

        Returns:
            Configured AIService instance
        """
        if isinstance(provider, str):
            provider = AIProvider(provider.lower())

        # Get settings based on provider
        api_key = None
        api_base = None
        api_version = None
        default_model = None

        if provider == AIProvider.OPENAI:
            api_key = getattr(settings, "OPENAI_API_KEY", None)
            api_base = getattr(settings, "OPENAI_API_BASE", None)
            default_model = getattr(settings, "OPENAI_MODEL", "gpt-4o")

        elif provider == AIProvider.AZURE_OPENAI:
            api_key = getattr(settings, "AZURE_OPENAI_API_KEY", None)
            api_base = getattr(settings, "AZURE_OPENAI_ENDPOINT", None)
            api_version = getattr(settings, "AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
            default_model = getattr(settings, "AZURE_OPENAI_DEPLOYMENT", None)

        elif provider == AIProvider.ANTHROPIC:
            api_key = getattr(settings, "ANTHROPIC_API_KEY", None)
            default_model = getattr(settings, "ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

        elif provider == AIProvider.GOOGLE:
            api_key = getattr(settings, "GOOGLE_AI_API_KEY", None)
            default_model = getattr(settings, "GOOGLE_AI_MODEL", "gemini-1.5-pro")

        config = AIModelConfig(
            provider=provider,
            model_name=model_name or default_model,
            api_key=override_params.get("api_key", api_key),
            api_base=override_params.get("api_base", api_base),
            api_version=override_params.get("api_version", api_version),
            temperature=override_params.get("temperature", 0.7),
            max_tokens=override_params.get("max_tokens", 4096),
            additional_params=override_params.get("additional_params", {}),
        )

        return cls.create(config)

    @classmethod
    def get_supported_providers(cls) -> list[str]:
        """Return list of supported provider names."""
        return [p.value for p in cls._providers.keys()]
