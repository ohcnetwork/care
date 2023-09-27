from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers

from care.facility.models import MedibaseMedicine, MedicineAdministration, Prescription
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


class PrescriptionSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)
    prescribed_by = UserBaseMinimumSerializer(read_only=True)
    last_administered_on = serializers.SerializerMethodField()
    medicine_object = MedibaseMedicineSerializer(read_only=True, source="medicine")
    medicine = serializers.UUIDField(write_only=True)

    def get_last_administered_on(self, obj):
        last_administration = (
            MedicineAdministration.objects.filter(prescription=obj)
            .order_by("-administered_date")
            .first()
        )
        if last_administration:
            return last_administration.administered_date
        return None

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
        if "medicine" in attrs:
            attrs["medicine"] = get_object_or_404(
                MedibaseMedicine, external_id=attrs["medicine"]
            )

        if not self.instance:
            if Prescription.objects.filter(
                consultation__external_id=self.context["request"].parser_context[
                    "kwargs"
                ]["consultation_external_id"],
                medicine=attrs["medicine"],
                discontinued=False,
            ).exists():
                raise serializers.ValidationError(
                    {
                        "medicine": (
                            "This medicine is already prescribed to this patient. "
                            "Please discontinue the existing prescription to prescribe again."
                        )
                    }
                )

        if attrs.get("is_prn"):
            if not attrs.get("indicator"):
                raise serializers.ValidationError(
                    {"indicator": "Indicator should be set for PRN prescriptions."}
                )
        else:
            if not attrs.get("frequency"):
                raise serializers.ValidationError(
                    {"frequency": "Frequency should be set for prescriptions."}
                )
        return super().validate(attrs)
        # TODO: Ensure that this medicine is not already prescribed to the same patient and is currently active.


class MedicineAdministrationSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)

    administered_by = UserBaseMinimumSerializer(read_only=True)
    prescription = PrescriptionSerializer(read_only=True)
    archived_by = UserBaseMinimumSerializer(read_only=True)

    def validate_administered_date(self, value):
        if value > timezone.now():
            raise serializers.ValidationError(
                "Administered Date cannot be in the future."
            )
        if self.context["prescription"].created_date > value:
            raise serializers.ValidationError(
                "Administered Date cannot be before Prescription Date."
            )
        return value

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
