from django.shortcuts import get_object_or_404
from rest_framework import serializers

from care.facility.models import MedibaseMedicine, MedicineAdministration, Prescription
from care.users.api.serializers.user import UserBaseMinimumSerializer
from care.users.models import User


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


class PrescriptionDetailSerializer(serializers.ModelSerializer):
    # TODO: Remove when #5492 is merged
    id = serializers.UUIDField(source="external_id", read_only=True)
    prescribed_by = UserBaseMinimumSerializer(read_only=True)
    last_administered_on = serializers.SerializerMethodField()
    medicine_object = MedibaseMedicineSerializer(read_only=True, source="medicine")
    medicine = serializers.UUIDField(write_only=True)

    def get_last_administered_on(self, obj):
        last_administration = (
            MedicineAdministration.objects.filter(prescription=obj)
            .order_by("-created_date")
            .first()
        )
        if last_administration:
            return last_administration.created_date
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


class MedicineAdministrationDetailSerializer(serializers.ModelSerializer):
    # TODO: Remove when #5492 is merged
    id = serializers.UUIDField(source="external_id", read_only=True)

    administered_by = UserBaseMinimumSerializer(read_only=True)
    prescription = PrescriptionDetailSerializer(read_only=True)

    class Meta:
        model = MedicineAdministration
        exclude = ("deleted",)
        read_only_fields = (
            "external_id",
            "administered_by",
            "created_date",
            "modified_date",
            "prescription",
        )


class MedibaseMedicineBareMinimumSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)

    class Meta:
        model = MedibaseMedicine
        fields = ["id", "name", "created_date", "modified_date"]
        read_only_fields = (
            "created_date",
            "modified_date",
        )


class PrescriptionBareMinimumSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)
    medicine_object = MedibaseMedicineBareMinimumSerializer(
        read_only=True, source="medicine"
    )

    class Meta:
        model = Prescription
        fields = (
            "id",
            "medicine_object",
            "medicine_old",
            "created_date",
        )


class MedicineAdministrationUserBareMinimumSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "first_name", "last_name"]


class MedicineAdministrationListSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)

    administered_by = MedicineAdministrationUserBareMinimumSerializer(read_only=True)
    prescription = PrescriptionBareMinimumSerializer(read_only=True)

    class Meta:
        model = MedicineAdministration
        fields = [
            "id",
            "prescription",
            "created_date",
            "administered_by",
            "notes",
            "modified_date",
        ]
        read_only_fields = (
            "id",
            "administered_by",
            "created_date",
            "prescription",
            "notes",
            "modified_date",
        )


class PrescriptionListSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)
    last_administered_on = serializers.SerializerMethodField()
    medicine_object = MedibaseMedicineBareMinimumSerializer(
        read_only=True, source="medicine"
    )

    class Meta:
        model = Prescription
        exclude = [
            "created_date",
            "external_id",
            "deleted",
            "meta",
            "discontinued_date",
            "is_migrated",
            "consultation",
            "medicine",
            "prescribed_by",
        ]

    def get_last_administered_on(self, obj):
        last_administration = (
            MedicineAdministration.objects.filter(prescription=obj)
            .order_by("-created_date")
            .first()
        )
        if last_administration:
            return last_administration.created_date
        return None
