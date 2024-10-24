from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers

from care.facility.models import (
    MedibaseMedicine,
    MedicineAdministration,
    Prescription,
    PrescriptionDosageType,
)
from care.users.api.serializers.user import UserBaseMinimumSerializer
import re


class MedibaseMedicineSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)

    class Meta:
        model = MedibaseMedicine
        exclude = ("deleted",)
        read_only_fields = (
            "external_id",
            "created_date",
            "modified_date",
        )


class MedicineAdministrationSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)

    administered_by = UserBaseMinimumSerializer(read_only=True)
    archived_by = UserBaseMinimumSerializer(read_only=True)

    def validate_administered_date(self, value):
        if value > timezone.now():
            msg = "Administered Date cannot be in the future."
            raise serializers.ValidationError(msg)
        if self.context["prescription"].created_date > value:
            msg = "Administered Date cannot be before Prescription Date."
            raise serializers.ValidationError(msg)
        return value

    def validate(self, attrs):
        if (
            not attrs.get("dosage")
            and self.context["prescription"].dosage_type
            == PrescriptionDosageType.TITRATED
        ):
            raise serializers.ValidationError(
                {"dosage": "Dosage is required for titrated prescriptions."}
            )
        if self.context["prescription"].dosage_type != PrescriptionDosageType.TITRATED:
            attrs.pop("dosage", None)

        return super().validate(attrs)

    def create(self, validated_data):
        if validated_data["prescription"].consultation.discharge_date:
            raise serializers.ValidationError(
                {"consultation": "Not allowed for discharged consultations"}
            )
        return super().create(validated_data)

    class Meta:
        model = MedicineAdministration
        exclude = ("deleted",)
        read_only_fields = (
            "external_id",
            "administered_by",
            "archived_by",
            "archived_on",
            "created_date",
            "modified_date",
            "prescription",
        )


class PrescriptionSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)
    prescribed_by = UserBaseMinimumSerializer(read_only=True)
    last_administration = MedicineAdministrationSerializer(read_only=True)
    medicine_object = MedibaseMedicineSerializer(read_only=True, source="medicine")
    medicine = serializers.UUIDField(write_only=True)

    class Meta:
        model = Prescription
        exclude = (
            "consultation",
            "deleted",
        )
        read_only_fields = (
            "medicine_old",
            "external_id",
            "prescribed_by",
            "created_date",
            "modified_date",
            "discontinued_date",
            "is_migrated",
        )

    def validate(self, attrs):
        def extract_numeric_value(dosage):

            match = re.match(r"(\d+(\.\d+)?)", dosage)  # Matches digits and optional decimal part
            if match:
                return float(match.group(1))

        if "medicine" in attrs:
            attrs["medicine"] = get_object_or_404(
                MedibaseMedicine, external_id=attrs["medicine"]
            )

        if (
            not self.instance
            and Prescription.objects.filter(
                consultation__external_id=self.context["request"].parser_context[
                    "kwargs"
                ]["consultation_external_id"],
                medicine=attrs["medicine"],
                discontinued=False,
            ).exists()
        ):
            raise serializers.ValidationError(
                {
                    "medicine": (
                        "This medicine is already prescribed to this patient. "
                        "Please discontinue the existing prescription to prescribe again."
                    )
                }
            )

        if not attrs.get("base_dosage"):
            raise serializers.ValidationError(
                {"base_dosage": "Base dosage is required."}
            )

            # Validate max_dosage is greater than or equal to base_dosage
        base_dosage = attrs.get("base_dosage")
        max_dosage = attrs.get("max_dosage")

        if base_dosage and max_dosage:
            # Extract numeric values from dosage strings
            base_dosage_value = extract_numeric_value(base_dosage)
            max_dosage_value = extract_numeric_value(max_dosage)

            # Raise error if max_dosage is less than base_dosage
            if max_dosage_value < base_dosage_value:
                raise serializers.ValidationError(
                    {"max_dosage": "Max dosage in 24 hours should be greater than or equal to base dosage."}
                )

        if attrs.get("dosage_type") == PrescriptionDosageType.PRN:
            if not attrs.get("indicator"):
                raise serializers.ValidationError(
                    {"indicator": "Indicator should be set for PRN prescriptions."}
                )
            attrs.pop("frequency", None)
            attrs.pop("days", None)
        else:
            if not attrs.get("frequency"):
                raise serializers.ValidationError(
                    {"frequency": "Frequency should be set for prescriptions."}
                )
            attrs.pop("indicator", None)
            attrs.pop("max_dosage", None)
            attrs.pop("min_hours_between_doses", None)

            if attrs.get("dosage_type") == PrescriptionDosageType.TITRATED:
                if not attrs.get("target_dosage"):
                    raise serializers.ValidationError(
                        {
                            "target_dosage": "Target dosage should be set for titrated prescriptions."
                        }
                    )
            else:
                attrs.pop("target_dosage", None)

        return super().validate(attrs)

    def create(self, validated_data):
        if validated_data["consultation"].discharge_date:
            raise serializers.ValidationError(
                {"consultation": "Not allowed for discharged consultations"}
            )
        return super().create(validated_data)
