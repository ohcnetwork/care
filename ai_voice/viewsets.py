from django.db.models import Count
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from ai_voice.models import SOAPNote, TranscriptionSession
from ai_voice.serializers import (
    SOAPNoteSerializer,
    SOAPNoteUpdateSerializer,
    TranscriptionSessionCreateSerializer,
    TranscriptionSessionListSerializer,
    TranscriptionSessionSerializer,
)
from ai_voice.tasks import generate_soap_note
from care.emr.models.encounter import Encounter


class TranscriptionSessionViewSet(GenericViewSet):
    permission_classes = [IsAuthenticated]
    lookup_field = "external_id"

    def get_queryset(self):
        return (
            TranscriptionSession.objects.select_related(
                "encounter", "initiated_by"
            )
            .prefetch_related("segments", "soap_notes")
            .filter(initiated_by=self.request.user)
        )

    def get_serializer_class(self):
        if self.action == "create":
            return TranscriptionSessionCreateSerializer
        if self.action == "list":
            return TranscriptionSessionListSerializer
        return TranscriptionSessionSerializer

    def list(self, request):
        encounter_id = request.query_params.get("encounter_id")
        qs = self.get_queryset().annotate(
            soap_note_count=Count("soap_notes"),
            segment_count=Count("segments"),
        )
        if encounter_id:
            qs = qs.filter(encounter__external_id=encounter_id)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    def retrieve(self, request, external_id=None):
        session = self.get_object()
        serializer = TranscriptionSessionSerializer(session)
        return Response(serializer.data)

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        encounter_id = serializer.validated_data["encounter_id"]

        try:
            encounter = Encounter.objects.get(external_id=encounter_id)
        except Encounter.DoesNotExist:
            return Response(
                {"error": "Encounter not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        session = TranscriptionSession.objects.create(
            encounter=encounter,
            initiated_by=request.user,
            status=TranscriptionSession.Status.CREATED,
        )
        return Response(
            TranscriptionSessionSerializer(session).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def complete(self, request, external_id=None):
        """Mark a transcription session as completed and build full transcript."""
        session = self.get_object()
        if session.status not in (
            TranscriptionSession.Status.RECORDING,
            TranscriptionSession.Status.TRANSCRIBING,
        ):
            return Response(
                {"error": f"Cannot complete session in '{session.status}' state"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        segments = session.segments.filter(is_final=True).order_by("start_time")
        full_transcript = "\n".join(
            f"[{seg.speaker or 'Speaker'}] {seg.text}" for seg in segments
        )
        session.transcript = full_transcript
        session.status = TranscriptionSession.Status.COMPLETED
        session.save(update_fields=["transcript", "status", "modified_date"])

        return Response(TranscriptionSessionSerializer(session).data)

    @action(detail=True, methods=["post"])
    def generate_notes(self, request, external_id=None):
        """Trigger SOAP note generation from the session transcript."""
        session = self.get_object()
        if not session.transcript:
            return Response(
                {"error": "No transcript available. Complete the session first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session.status = TranscriptionSession.Status.GENERATING_NOTES
        session.save(update_fields=["status", "modified_date"])

        soap_note = SOAPNote.objects.create(
            session=session,
            status=SOAPNote.Status.GENERATING,
        )

        generate_soap_note.delay(str(soap_note.external_id))

        return Response(
            SOAPNoteSerializer(soap_note).data,
            status=status.HTTP_202_ACCEPTED,
        )


class SOAPNoteViewSet(GenericViewSet):
    permission_classes = [IsAuthenticated]
    lookup_field = "external_id"

    def get_queryset(self):
        return SOAPNote.objects.select_related(
            "session", "session__encounter", "reviewed_by"
        ).filter(session__initiated_by=self.request.user)

    def get_serializer_class(self):
        if self.action in ("partial_update", "update"):
            return SOAPNoteUpdateSerializer
        return SOAPNoteSerializer

    def retrieve(self, request, external_id=None):
        note = self.get_object()
        return Response(SOAPNoteSerializer(note).data)

    def partial_update(self, request, external_id=None):
        """Allow editing SOAP note fields before review."""
        note = self.get_object()
        serializer = SOAPNoteUpdateSerializer(note, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(SOAPNoteSerializer(note).data)

    @action(detail=True, methods=["post"])
    def mark_reviewed(self, request, external_id=None):
        """Mark a SOAP note as reviewed by a physician."""
        from django.utils import timezone

        note = self.get_object()
        note.status = SOAPNote.Status.REVIEWED
        note.reviewed_by = request.user
        note.reviewed_at = timezone.now()
        note.save(
            update_fields=["status", "reviewed_by", "reviewed_at", "modified_date"]
        )
        return Response(SOAPNoteSerializer(note).data)
