import asyncio
import logging
from collections.abc import Callable

import assemblyai as aai
from django.conf import settings

logger = logging.getLogger(__name__)

MEDICAL_KEYTERMS = [
    "hypertension",
    "diabetes",
    "mellitus",
    "metformin",
    "systolic",
    "diastolic",
    "tachycardia",
    "bradycardia",
    "dyspnea",
    "edema",
    "auscultation",
    "palpation",
    "bilateral",
    "prognosis",
    "differential diagnosis",
    "hemoglobin",
    "creatinine",
    "troponin",
    "electrocardiogram",
    "echocardiogram",
    "spirometry",
    "anticoagulant",
    "analgesic",
    "antibiotic",
    "corticosteroid",
    "bronchodilator",
    "immunosuppressant",
    "acetaminophen",
    "ibuprofen",
    "amoxicillin",
    "atorvastatin",
    "lisinopril",
    "omeprazole",
    "levothyroxine",
    "amlodipine",
    "pneumonia",
    "sepsis",
    "anaphylaxis",
    "myocardial infarction",
    "cerebrovascular accident",
    "chronic obstructive pulmonary disease",
    "congestive heart failure",
    "deep vein thrombosis",
    "pulmonary embolism",
]


def get_assemblyai_api_key() -> str:
    """Get AssemblyAI API key from plugin config or settings."""
    plugin_configs = getattr(settings, "PLUGIN_CONFIGS", {})
    ai_voice_config = plugin_configs.get("ai_voice", {})
    return ai_voice_config.get(
        "ASSEMBLYAI_API_KEY",
        getattr(settings, "ASSEMBLYAI_API_KEY", ""),
    )


class RealtimeTranscriber:
    """Manages a real-time transcription session with AssemblyAI."""

    def __init__(
        self,
        on_transcript: Callable[[dict], None],
        on_error: Callable[[str], None],
        sample_rate: int = 16000,
    ):
        self.on_transcript = on_transcript
        self.on_error = on_error
        self.sample_rate = sample_rate
        self.transcriber = None
        self._is_active = False

    def start(self):
        """Initialize and start the AssemblyAI real-time transcriber."""
        api_key = get_assemblyai_api_key()
        if not api_key:
            self.on_error("AssemblyAI API key is not configured")
            return

        aai.settings.api_key = api_key

        def on_data(transcript: aai.RealtimeTranscript):
            if isinstance(transcript, aai.RealtimeFinalTranscript):
                self.on_transcript(
                    {
                        "text": transcript.text,
                        "confidence": transcript.confidence,
                        "start": transcript.audio_start / 1000.0,
                        "end": transcript.audio_end / 1000.0,
                        "is_final": True,
                    }
                )
            elif isinstance(transcript, aai.RealtimePartialTranscript):
                if transcript.text:
                    self.on_transcript(
                        {
                            "text": transcript.text,
                            "confidence": 0.0,
                            "start": transcript.audio_start / 1000.0,
                            "end": transcript.audio_end / 1000.0,
                            "is_final": False,
                        }
                    )

        def on_error(error: aai.RealtimeError):
            logger.error("AssemblyAI error: %s", error)
            self.on_error(str(error))

        self.transcriber = aai.RealtimeTranscriber(
            sample_rate=self.sample_rate,
            on_data=on_data,
            on_error=on_error,
            word_boost=MEDICAL_KEYTERMS,
            encoding=aai.AudioEncoding.pcm_s16le,
        )
        self.transcriber.connect()
        self._is_active = True

    def stream(self, audio_data: bytes):
        """Send audio data to the transcriber."""
        if self.transcriber and self._is_active:
            self.transcriber.stream(audio_data)

    def close(self):
        """Close the transcription session."""
        self._is_active = False
        if self.transcriber:
            try:
                self.transcriber.close()
            except Exception:
                logger.exception("Error closing AssemblyAI transcriber")
            self.transcriber = None


def transcribe_audio_file(audio_url: str) -> dict:
    """Transcribe an audio file (non-realtime) using AssemblyAI.

    Returns dict with 'text', 'utterances', and 'confidence'.
    """
    api_key = get_assemblyai_api_key()
    if not api_key:
        raise ValueError("AssemblyAI API key is not configured")

    aai.settings.api_key = api_key

    config = aai.TranscriptionConfig(
        speaker_labels=True,
        word_boost=MEDICAL_KEYTERMS,
        boost_param=aai.WordBoost.high,
    )

    transcriber = aai.Transcriber(config=config)
    transcript = transcriber.transcribe(audio_url)

    if transcript.status == aai.TranscriptStatus.error:
        raise RuntimeError(f"Transcription failed: {transcript.error}")

    utterances = []
    if transcript.utterances:
        for utt in transcript.utterances:
            utterances.append(
                {
                    "speaker": utt.speaker,
                    "text": utt.text,
                    "start": utt.start / 1000.0,
                    "end": utt.end / 1000.0,
                    "confidence": utt.confidence,
                }
            )

    return {
        "text": transcript.text,
        "utterances": utterances,
        "confidence": transcript.confidence,
    }
