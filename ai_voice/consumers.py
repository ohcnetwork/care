import json
import logging
import threading

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from ai_voice.models import TranscriptionSegment, TranscriptionSession
from ai_voice.utils.transcription import RealtimeTranscriber

logger = logging.getLogger(__name__)


class TranscriptionConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time audio transcription.

    Protocol:
    - Client sends binary audio frames (PCM 16-bit, 16kHz, mono)
    - Client sends JSON text messages for control: {"type": "start"}, {"type": "stop"}
    - Server sends JSON text messages with transcription results and status updates
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session_id = None
        self.session = None
        self.transcriber = None
        self.user = None

    async def connect(self):
        self.session_id = self.scope["url_route"]["kwargs"]["session_id"]
        self.user = self.scope.get("user")

        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return

        try:
            self.session = await self._get_session()
        except TranscriptionSession.DoesNotExist:
            await self.close(code=4004)
            return

        await self.accept()
        await self.send_json({"type": "connected", "session_id": self.session_id})

    async def disconnect(self, code):
        await self._stop_transcription()

    async def receive(self, text_data=None, bytes_data=None):
        if bytes_data:
            # Binary audio data - forward to AssemblyAI
            if self.transcriber:
                self.transcriber.stream(bytes_data)
            return

        if text_data:
            try:
                message = json.loads(text_data)
            except json.JSONDecodeError:
                await self.send_json({"type": "error", "message": "Invalid JSON"})
                return

            msg_type = message.get("type")

            if msg_type == "start":
                await self._start_transcription()
            elif msg_type == "stop":
                await self._stop_transcription()
                await self._complete_session()
            elif msg_type == "ping":
                await self.send_json({"type": "pong"})

    async def _start_transcription(self):
        if self.transcriber:
            return

        await self._update_session_status(TranscriptionSession.Status.RECORDING)

        def on_transcript(data):
            """Callback from AssemblyAI - runs in transcriber thread."""
            import asyncio

            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()

            asyncio.run_coroutine_threadsafe(
                self._handle_transcript(data), loop
            )

        def on_error(error_msg):
            import asyncio

            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()

            asyncio.run_coroutine_threadsafe(
                self.send_json({"type": "error", "message": error_msg}), loop
            )

        self.transcriber = RealtimeTranscriber(
            on_transcript=on_transcript,
            on_error=on_error,
        )

        # Start transcriber in a background thread
        thread = threading.Thread(target=self.transcriber.start, daemon=True)
        thread.start()

        await self.send_json({"type": "recording_started"})

    async def _stop_transcription(self):
        if self.transcriber:
            self.transcriber.close()
            self.transcriber = None
            await self.send_json({"type": "recording_stopped"})

    async def _handle_transcript(self, data):
        """Process transcript data from AssemblyAI."""
        await self.send_json(
            {
                "type": "transcript",
                "text": data["text"],
                "confidence": data["confidence"],
                "start_time": data["start"],
                "end_time": data["end"],
                "is_final": data["is_final"],
            }
        )

        if data["is_final"] and data["text"].strip():
            await self._save_segment(data)

    @database_sync_to_async
    def _get_session(self):
        return TranscriptionSession.objects.get(external_id=self.session_id)

    @database_sync_to_async
    def _update_session_status(self, new_status):
        self.session.status = new_status
        self.session.save(update_fields=["status", "modified_date"])

    @database_sync_to_async
    def _save_segment(self, data):
        TranscriptionSegment.objects.create(
            session=self.session,
            text=data["text"],
            start_time=data["start"],
            end_time=data["end"],
            confidence=data["confidence"],
            is_final=True,
        )

    async def _complete_session(self):
        await self._update_session_status(TranscriptionSession.Status.COMPLETED)
        segments = await self._get_segments()
        transcript = "\n".join(f"[Speaker] {seg['text']}" for seg in segments)
        await self._save_transcript(transcript)
        await self.send_json(
            {
                "type": "session_completed",
                "transcript": transcript,
            }
        )

    @database_sync_to_async
    def _get_segments(self):
        return list(
            self.session.segments.filter(is_final=True)
            .order_by("start_time")
            .values("text", "start_time", "end_time", "speaker")
        )

    @database_sync_to_async
    def _save_transcript(self, transcript):
        self.session.transcript = transcript
        self.session.save(update_fields=["transcript", "modified_date"])

    async def send_json(self, data):
        await self.send(text_data=json.dumps(data))
