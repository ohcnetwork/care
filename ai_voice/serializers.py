from rest_framework import serializers

from ai_voice.models import SOAPNote, TranscriptionSegment, TranscriptionSession


class TranscriptionSegmentSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)

    class Meta:
        model = TranscriptionSegment
        fields = [
            "id",
            "text",
            "start_time",
            "end_time",
            "confidence",
            "speaker",
            "is_final",
            "created_date",
        ]
        read_only_fields = fields


class SOAPNoteSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)
    session_id = serializers.UUIDField(source="session.external_id", read_only=True)

    class Meta:
        model = SOAPNote
        fields = [
            "id",
            "session_id",
            "status",
            "subjective",
            "objective",
            "assessment",
            "plan",
            "summary",
            "reviewed_by",
            "reviewed_at",
            "created_date",
            "modified_date",
        ]
        read_only_fields = [
            "id",
            "session_id",
            "status",
            "created_date",
            "modified_date",
        ]


class SOAPNoteUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SOAPNote
        fields = [
            "subjective",
            "objective",
            "assessment",
            "plan",
            "summary",
        ]


class TranscriptionSessionSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)
    encounter_id = serializers.UUIDField(
        source="encounter.external_id", read_only=True
    )
    initiated_by_name = serializers.CharField(
        source="initiated_by.get_full_name", read_only=True
    )
    segments = TranscriptionSegmentSerializer(many=True, read_only=True)
    soap_notes = SOAPNoteSerializer(many=True, read_only=True)

    class Meta:
        model = TranscriptionSession
        fields = [
            "id",
            "encounter_id",
            "initiated_by_name",
            "status",
            "duration_seconds",
            "transcript",
            "segments",
            "soap_notes",
            "created_date",
            "modified_date",
        ]
        read_only_fields = fields


class TranscriptionSessionCreateSerializer(serializers.Serializer):
    encounter_id = serializers.UUIDField()


class TranscriptionSessionListSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)
    encounter_id = serializers.UUIDField(
        source="encounter.external_id", read_only=True
    )
    initiated_by_name = serializers.CharField(
        source="initiated_by.get_full_name", read_only=True
    )
    soap_note_count = serializers.IntegerField(read_only=True)
    segment_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = TranscriptionSession
        fields = [
            "id",
            "encounter_id",
            "initiated_by_name",
            "status",
            "duration_seconds",
            "soap_note_count",
            "segment_count",
            "created_date",
            "modified_date",
        ]
        read_only_fields = fields
