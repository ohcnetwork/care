from django.urls import re_path

from ai_voice.consumers import TranscriptionConsumer

websocket_urlpatterns = [
    re_path(
        r"ws/transcription/(?P<session_id>[0-9a-f-]+)/$",
        TranscriptionConsumer.as_asgi(),
    ),
]
