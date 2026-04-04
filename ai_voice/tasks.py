import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def generate_soap_note(self, soap_note_external_id: str):
    """Async task to generate a SOAP note from a transcription session."""
    from ai_voice.models import SOAPNote, TranscriptionSession
    from ai_voice.utils.soap_generator import generate_soap_from_transcript

    try:
        note = SOAPNote.objects.select_related("session").get(
            external_id=soap_note_external_id
        )
    except SOAPNote.DoesNotExist:
        logger.error("SOAPNote %s not found", soap_note_external_id)
        return

    session = note.session

    try:
        result = generate_soap_from_transcript(session.transcript)

        note.subjective = result["subjective"]
        note.objective = result["objective"]
        note.assessment = result["assessment"]
        note.plan = result["plan"]
        note.summary = result["summary"]
        note.raw_response = result
        note.meta = result.get("meta", {})
        note.status = SOAPNote.Status.COMPLETED
        note.save(
            update_fields=[
                "subjective",
                "objective",
                "assessment",
                "plan",
                "summary",
                "raw_response",
                "meta",
                "status",
                "modified_date",
            ]
        )

        session.status = TranscriptionSession.Status.COMPLETED
        session.save(update_fields=["status", "modified_date"])

        logger.info("SOAP note generated for session %s", session.external_id)

    except Exception as exc:
        logger.exception(
            "Failed to generate SOAP note for %s", soap_note_external_id
        )
        note.status = SOAPNote.Status.FAILED
        note.meta = {"error": str(exc)}
        note.save(update_fields=["status", "meta", "modified_date"])

        session.status = TranscriptionSession.Status.FAILED
        session.save(update_fields=["status", "modified_date"])

        raise self.retry(exc=exc)
