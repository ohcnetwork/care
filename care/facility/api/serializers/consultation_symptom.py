from copy import copy

from django.db import transaction
from rest_framework import serializers

from care.facility.events.handler import create_consultation_events
from care.facility.models.consultation_symptom import ConsultationSymptom, Symptom
from care.users.api.serializers.user import UserBaseMinimumSerializer


class ConsultationSymptomSerializers(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)
    created_by = UserBaseMinimumSerializer(read_only=True)
    updated_by = UserBaseMinimumSerializer(read_only=True)

    class Meta:
        model = ConsultationSymptom
        exclude = (
            "daily_round",
            "consultation",
            "external_id",
            "deleted",
        )
        read_only_fields = (
            "created_date",
            "modified_date",
            "is_migrated",
        )

    def validate(self, attrs):
        validated_data = super().validate(attrs)
        consultation = (
            self.instance.consultation
            if self.instance
            else self.context["consultation"]
        )

        onset_date = (
            self.instance.onset_date
            if self.instance
            else validated_data.get("onset_date")
        )
        if cure_date := validated_data.get("cure_date"):
            if cure_date < onset_date:
                raise serializers.ValidationError(
                    {"cure_date": "Cure date should be after onset date"}
                )

        if (
            validated_data.get("other_symptom")
            and validated_data.get("symptom") != Symptom.OTHERS
        ):
            raise serializers.ValidationError(
                {
                    "other_symptom": "Other symptom should be empty when symptom is not OTHERS"
                }
            )

        if ConsultationSymptom.objects.filter(
            consultation=consultation,
            symptom=validated_data.get("symptom"),
            other_symptom=validated_data.get("other_symptom"),
            cure_date__isnull=True,
        ).exists():
            raise serializers.ValidationError(
                {"symptom": "An active symptom with the same details already exists"}
            )

        return validated_data

    def create(self, validated_data):
        validated_data["consultation"] = self.context["consultation"]
        validated_data["created_by"] = self.context["request"].user

        with transaction.atomic():
            instance: ConsultationSymptom = super().create(validated_data)

            create_consultation_events(
                instance.consultation_id,
                instance,
                instance.created_by_id,
                instance.created_date,
            )

            return instance

    def update(self, instance, validated_data):
        validated_data["updated_by"] = self.context["request"].user

        with transaction.atomic():
            old_instance = copy(instance)
            instance = super().update(instance, validated_data)

            create_consultation_events(
                instance.consultation_id,
                instance,
                instance.updated_by_id,
                instance.modified_date,
                old_instance=old_instance,
            )

            return instance


class ConsultationCreateSymptomSerializers(serializers.ModelSerializer):
    class Meta:
        model = ConsultationSymptom
        fields = ("symptom", "other_symptom", "onset_date")
