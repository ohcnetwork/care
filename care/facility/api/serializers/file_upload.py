from care.facility.models.patient_sample import PatientSample
from care.facility.api.serializers import facility
from django.core.exceptions import ValidationError
from django.db.models import F
from rest_framework import serializers


from care.facility.models.file_upload import FileUpload

from care.users.api.serializers.user import UserBaseMinimumSerializer
from config.serializers import ChoiceField
from care.facility.models.file_upload import FileUpload

from care.facility.models.patient import PatientRegistration
from care.facility.models.patient_consultation import PatientConsultation

from care.users.api.serializers.user import UserBaseMinimumSerializer

from care.facility.api.serializers.shifting import has_facility_permission


def check_permissions(file_type, associating_id, user):
    try:
        if file_type == FileUpload.FileType.PATIENT.value:
            patient = PatientRegistration.objects.get(external_id=associating_id)
            if patient.last_consultation:
                if patient.last_consultation.assigned_to:
                    if user == patient.last_consultation.assigned_to:
                        return patient.id
            if not has_facility_permission(user, patient.facility):
                raise Exception("No Permission")
            return patient.id
        elif file_type == FileUpload.FileType.CONSULTATION.value:
            consultation = PatientConsultation.objects.get(external_id=associating_id)
            if consultation.assigned_to:
                if user == consultation.assigned_to:
                    return consultation.id
            if not (
                has_facility_permission(user, consultation.patient.facility)
                or has_facility_permission(user, consultation.facility)
            ):
                raise Exception("No Permission")
            return consultation.id
        elif file_type == FileUpload.FileType.SAMPLE_MANAGEMENT.value:
            sample = PatientSample.objects.get(external_id=associating_id)
            patient = sample.patient
            if sample.consultation:
                if sample.consultation.assigned_to:
                    if user == sample.consultation.assigned_to:
                        return sample.id
            if not has_facility_permission(user, patient.facility):
                raise Exception("No Permission")
            return sample.id
        else:
            raise Exception("Undefined File Type")

    except Exception:
        raise serializers.ValidationError({"permission": "denied"})


class FileUploadCreateSerializer(serializers.ModelSerializer):

    file_type = ChoiceField(choices=FileUpload.FileTypeChoices)
    file_category = ChoiceField(choices=FileUpload.FileCategoryChoices, required=False)

    signed_url = serializers.CharField(read_only=True)
    associating_id = serializers.CharField(write_only=True)
    internal_name = serializers.CharField(read_only=True)
    original_name = serializers.CharField(write_only=True)

    class Meta:
        model = FileUpload
        fields = (
            "file_type",
            "file_category",
            "name",
            "associating_id",
            "signed_url",
            "internal_name",
            "original_name",
        )
        write_only_fields = ("associating_id",)

    def create(self, validated_data):
        user = self.context["request"].user
        internal_id = check_permissions(validated_data["file_type"], validated_data["associating_id"], user)
        validated_data["associating_id"] = internal_id
        validated_data["uploaded_by"] = user
        validated_data["internal_name"] = validated_data["original_name"]
        del validated_data["original_name"]
        return super().create(validated_data)


class FileUploadListSerializer(serializers.ModelSerializer):

    id = serializers.UUIDField(source="external_id", read_only=True)

    uploaded_by = UserBaseMinimumSerializer(read_only=True)

    class Meta:
        model = FileUpload
        fields = ("id", "name", "uploaded_by", "created_date", "file_category")
        read_only_fields = ("associating_id", "name", "created_date")


class FileUploadRetrieveSerializer(serializers.ModelSerializer):

    id = serializers.UUIDField(source="external_id", read_only=True)

    uploaded_by = UserBaseMinimumSerializer(read_only=True)
    read_signed_url = serializers.CharField(read_only=True)

    class Meta:
        model = FileUpload
        fields = ("id", "name", "uploaded_by", "created_date", "read_signed_url", "file_category")
        read_only_fields = ("associating_id", "name", "created_date")
