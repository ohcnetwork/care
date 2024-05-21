from copy import copy

from django.db import transaction
from django.utils.timezone import now
from rest_framework import serializers

from care.facility.events.handler import create_consultation_events
from care.facility.models.encounter_symptom import (
    ClinicalImpressionStatus,
    EncounterSymptom,
    Symptom,
)
from care.users.api.serializers.user import UserBaseMinimumSerializer


class EncounterSymptomSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)
    created_by = UserBaseMinimumSerializer(read_only=True)
    updated_by = UserBaseMinimumSerializer(read_only=True)

    class Meta:
        model = EncounterSymptom
        exclude = (
            "consultation",
            "external_id",
            "deleted",
        )
        read_only_fields = (
            "created_date",
            "modified_date",
            "is_migrated",
        )

    def validate_onset_date(self, value):
        if value and value > now():
            raise serializers.ValidationError("Onset date cannot be in the future")
        return value

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

        if validated_data.get("symptom") != Symptom.OTHERS and validated_data.get(
            "other_symptom"
        ):
            raise serializers.ValidationError(
                {
                    "other_symptom": "Other symptom should be empty when symptom type is not OTHERS"
                }
            )

        if validated_data.get("symptom") == Symptom.OTHERS and not validated_data.get(
            "other_symptom"
        ):
            raise serializers.ValidationError(
                {
                    "other_symptom": "Other symptom should not be empty when symptom type is OTHERS"
                }
            )

        if EncounterSymptom.objects.filter(
            consultation=consultation,
            symptom=validated_data.get("symptom"),
            other_symptom=validated_data.get("other_symptom") or "",
            cure_date__isnull=True,
            clinical_impression_status=ClinicalImpressionStatus.IN_PROGRESS,
        ).exists():
            raise serializers.ValidationError(
                {"symptom": "An active symptom with the same details already exists"}
            )

        return validated_data

    def create(self, validated_data):
        validated_data["consultation"] = self.context["consultation"]
        validated_data["created_by"] = self.context["request"].user

        with transaction.atomic():
            instance: EncounterSymptom = super().create(validated_data)

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
                old=old_instance,
            )

            return instance


class EncounterCreateSymptomSerializer(serializers.ModelSerializer):
    class Meta:
        model = EncounterSymptom
        fields = ("symptom", "other_symptom", "onset_date", "cure_date")
