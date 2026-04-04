from rest_framework.routers import DefaultRouter

from ai_voice.viewsets import SOAPNoteViewSet, TranscriptionSessionViewSet

router = DefaultRouter()
router.register("sessions", TranscriptionSessionViewSet, basename="transcription-session")
router.register("soap-notes", SOAPNoteViewSet, basename="soap-note")

urlpatterns = router.urls
