# AI Voice - Medical Transcription Plugin for CARE

Real-time medical transcription and AI-powered clinical documentation plugin for the [CARE](https://github.com/ohcnetwork/care) platform.

## Features

- **Real-time audio transcription** via AssemblyAI with medical vocabulary boosting
- **WebSocket streaming** for live transcription display during patient encounters
- **AI-powered SOAP note generation** using LLM (GPT-4o or compatible)
- **Encounter integration** - transcriptions linked directly to patient encounters
- **Physician review workflow** - SOAP notes require review before finalization
- **Speaker identification** - distinguishes provider and patient speech when available

## Architecture

```
Browser (Mic) → WebSocket → Django Channels Consumer → AssemblyAI Streaming API
                                    ↓
                            TranscriptionSegments (DB)
                                    ↓
                         Full Transcript Assembly
                                    ↓
                    Celery Task → LLM (GPT-4o) → SOAP Note
                                    ↓
                         Physician Review & Approval
```

## Configuration

Add to your `plug_config.py`:

```python
from plugs.plug import Plug

ai_voice = Plug(
    name="ai_voice",
    package_name="git+https://github.com/ohcnetwork/ai_voice.git",
    version="@main",
    configs={
        "ASSEMBLYAI_API_KEY": "your-assemblyai-key",
        "OPENAI_API_KEY": "your-openai-key",
        "LLM_MODEL": "gpt-4o",
        "LLM_TEMPERATURE": 0.2,
        # Optional: custom OpenAI-compatible endpoint
        # "OPENAI_BASE_URL": "https://your-gateway.com/v1",
    },
)
```

## API Endpoints

All endpoints are under `/api/ai_voice/`:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/sessions/` | List transcription sessions |
| POST | `/sessions/` | Create new session (requires `encounter_id`) |
| GET | `/sessions/{id}/` | Get session with segments and notes |
| POST | `/sessions/{id}/complete/` | Complete session and assemble transcript |
| POST | `/sessions/{id}/generate_notes/` | Generate SOAP note from transcript |
| GET | `/soap-notes/{id}/` | Get a SOAP note |
| PATCH | `/soap-notes/{id}/` | Edit SOAP note fields |
| POST | `/soap-notes/{id}/mark_reviewed/` | Mark note as physician-reviewed |

## WebSocket

Connect to `ws://host/ws/transcription/{session_id}/` for real-time streaming.

**Send:** Binary PCM audio (16-bit, 16kHz, mono) or JSON control messages
**Receive:** JSON transcription results and status updates

## Requirements

- Python 3.13+
- CARE platform
- Redis (for Django Channels)
- AssemblyAI API key
- OpenAI API key (or compatible LLM provider)
