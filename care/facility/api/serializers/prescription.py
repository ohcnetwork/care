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
    # Class-level constants for field names
    PRN_FIELDS = {"indicator"}
    TITRATED_FIELDS = {"target_dosage"}
    STANDARD_FIELDS = {"frequency", "days"}

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

    def _remove_irrelevant_fields(self, attrs, keep_fields):
        """Remove fields not relevant for the current dosage type"""
        all_fields = self.PRN_FIELDS | self.TITRATED_FIELDS | self.STANDARD_FIELDS
        for field in all_fields - keep_fields:
            attrs.pop(field, None)

    def validate_medicine(self, attrs):
        """Validate the medicine field and check for duplicate prescriptions."""
        attrs["medicine"] = get_object_or_404(
            MedibaseMedicine, external_id=attrs["medicine"]
        )

        # Check for existing prescription
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
                        "Discontinue the existing prescription to prescribe again."
                    )
                }
            )

    def validate_dosage(self, attrs):
        """Validate base and max dosage."""
        base_dosage = attrs.get("base_dosage")
        max_dosage = attrs.get("max_dosage")

        if not base_dosage:
            raise serializers.ValidationError(
                {"base_dosage": "Base dosage is required"}
            )

        if max_dosage:
            if not base_dosage:
                raise serializers.ValidationError(
                    {"max_dosage": "Max dosage cannot be set without base dosage"}
                )
            try:
                base_dosage_value, base_unit = self.parse_dosage(base_dosage)
                max_dosage_value, max_unit = self.parse_dosage(max_dosage)

                if base_unit != max_unit:
                    raise serializers.ValidationError(
                        {
                            "max_dosage": f"Max dosage units ({max_unit}) must match base dosage units ({base_unit})."
                        }
                    )

                if max_dosage_value < base_dosage_value:
                    raise serializers.ValidationError(
                        {
                            "max_dosage": "Max dosage in 24 hours should be greater than or equal to base dosage."
                        }
                    )
            except ValueError as e:
                raise serializers.ValidationError(
                    {
                        "max_dosage": "Invalid dosage format. Expected format: 'number unit' (e.g., '500 mg')"
                    }
                ) from e

    def validate_dosage_type_specific(self, attrs):
        """Validate fields specific to dosage types."""
        dosage_type = attrs.get("dosage_type")

        if dosage_type == PrescriptionDosageType.PRN:
            if not attrs.get("indicator"):
                raise serializers.ValidationError(
                    {"indicator": "Indicator should be set for PRN prescriptions."}
                )
            # Remove irrelevant fields
            self._remove_irrelevant_fields(attrs, self.PRN_FIELDS)

        elif dosage_type == PrescriptionDosageType.TITRATED:
            if not attrs.get("target_dosage"):
                raise serializers.ValidationError(
                    {
                        "target_dosage": "Target dosage should be set for titrated prescriptions."
                    }
                )
            # Remove irrelevant fields
            self._remove_irrelevant_fields(attrs, self.TITRATED_FIELDS)

        else:
            if not attrs.get("frequency"):
                raise serializers.ValidationError(
                    {"frequency": "Frequency should be set for prescriptions."}
                )
            # Remove irrelevant fields
            self._remove_irrelevant_fields(attrs, self.STANDARD_FIELDS)

            # If it's not PRN or TITRATED, ensure standard fields are respected
            attrs.pop("indicator", None)
            attrs.pop("max_dosage", None)
            attrs.pop("min_hours_between_doses", None)
            attrs.pop("target_dosage", None)

    DOSAGE_PARTS_REQUIRED = 2  # Define a constant for the required parts in dosage

    def parse_dosage(self, dosage):
        """Parse the dosage into value and unit parts."""
        parts = dosage.split(" ", maxsplit=1)
        if len(parts) != self.DOSAGE_PARTS_REQUIRED:
            error_message = (
                f"Invalid dosage format. Expected 'number unit' but got '{dosage}'"
            )
            raise ValueError(error_message)
        value = float(parts[0])
        if value < 0:
            error_message = f"Dosage value cannot be negative: {value}"
            raise ValueError(error_message)
        return value, parts[1]

    def create(self, validated_data):
        if validated_data["consultation"].discharge_date:
            raise serializers.ValidationError(
                {"consultation": "Not allowed for discharged consultations"}
            )
        return super().create(validated_data)
