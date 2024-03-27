from rest_framework import serializers

from care.facility.models.ai import AIFormFill


class AIFormFillSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIFormFill
        fields = [
            "external_id",
            "requested_by",
            "transcript",
            "ai_response",
            "status",
            "form_data",
            "audio_file_ids",
        ]
        read_only_fields = [
            "external_id",
            "requested_by",
            "ai_response",
            "audio_file_ids",
        ]
