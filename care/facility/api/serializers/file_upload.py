from django.conf import settings
from django.utils.timezone import localtime, now
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from care.facility.api.serializers.shifting import has_facility_permission
from care.facility.models.facility import Facility
from care.facility.models.file_upload import FileUpload
from care.facility.models.notification import Notification
from care.facility.models.patient import PatientRegistration
from care.facility.models.patient_consultation import (
    PatientConsent,
    PatientConsultation,
)
from care.facility.models.patient_sample import PatientSample
from care.users.api.serializers.user import UserBaseMinimumSerializer
from care.users.models import User
from care.utils.notification_handler import NotificationGenerator
from care.utils.serializers.fields import ChoiceField


def check_permissions(file_type, associating_id, user, action="create"):  # noqa: PLR0911, PLR0912
    try:
        if file_type == FileUpload.FileType.PATIENT.value:
            patient = PatientRegistration.objects.get(external_id=associating_id)
            if not patient.is_active:
                raise serializers.ValidationError(
                    {"patient": "Cannot upload file for a discharged patient."}
                )
            if patient.assigned_to and user == patient.assigned_to:
                return patient.id
            if (
                patient.last_consultation
                and patient.last_consultation.assigned_to
                and user == patient.last_consultation.assigned_to
            ):
                return patient.id
            if not has_facility_permission(user, patient.facility):
                msg = "No Permission"
                raise Exception(msg)
            return patient.id
        if file_type == FileUpload.FileType.CONSULTATION.value:
            consultation = PatientConsultation.objects.get(external_id=associating_id)
            if consultation.discharge_date and not action == "read":
                raise serializers.ValidationError(
                    {
                        "consultation": "Cannot upload file for a discharged consultation."
                    }
                )
            if (
                consultation.patient.assigned_to
                and user == consultation.patient.assigned_to
            ):
                return consultation.id
            if consultation.assigned_to and user == consultation.assigned_to:
                return consultation.id
            if not (
                has_facility_permission(user, consultation.patient.facility)
                or has_facility_permission(user, consultation.facility)
            ):
                msg = "No Permission"
                raise Exception(msg)
            return consultation.id
        if file_type == FileUpload.FileType.CONSENT_RECORD.value:
            consultation = PatientConsent.objects.get(
                external_id=associating_id
            ).consultation
            if consultation.discharge_date and not action == "read":
                raise serializers.ValidationError(
                    {
                        "consultation": "Cannot upload file for a discharged consultation."
                    }
                )
            if (
                user in (consultation.assigned_to, consultation.patient.assigned_to)
                or has_facility_permission(user, consultation.facility)
                or has_facility_permission(user, consultation.patient.facility)
            ):
                return associating_id
            msg = "No Permission"
            raise Exception(msg)
        if file_type == FileUpload.FileType.DISCHARGE_SUMMARY.value:
            consultation = PatientConsultation.objects.get(external_id=associating_id)
            if (
                consultation.patient.assigned_to
                and user == consultation.patient.assigned_to
            ):
                return consultation.external_id
            if consultation.assigned_to and user == consultation.assigned_to:
                return consultation.external_id
            if not (
                has_facility_permission(user, consultation.patient.facility)
                or has_facility_permission(user, consultation.facility)
            ):
                msg = "No Permission"
                raise Exception(msg)
            return consultation.external_id
        if file_type == FileUpload.FileType.SAMPLE_MANAGEMENT.value:
            sample = PatientSample.objects.get(external_id=associating_id)
            patient = sample.patient
            if patient.assigned_to and user == patient.assigned_to:
                return sample.id
            if (
                sample.consultation
                and sample.consultation.assigned_to
                and user == sample.consultation.assigned_to
            ):
                return sample.id
            if sample.testing_facility and has_facility_permission(
                user,
                Facility.objects.get(external_id=sample.testing_facility.external_id),
            ):
                return sample.id
            if not has_facility_permission(user, patient.facility):
                msg = "No Permission"
                raise Exception(msg)
            return sample.id
        if file_type in (
            FileUpload.FileType.CLAIM.value,
            FileUpload.FileType.COMMUNICATION.value,
        ):
            return associating_id
        msg = "Undefined File Type"
        raise Exception(msg)

    except Exception as e:
        raise serializers.ValidationError({"permission": "denied"}) from e


class FileUploadCreateSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)
    file_type = ChoiceField(choices=FileUpload.FileTypeChoices)
    file_category = ChoiceField(choices=FileUpload.FileCategoryChoices, required=False)

    signed_url = serializers.CharField(read_only=True)
    associating_id = serializers.CharField(write_only=True)
    internal_name = serializers.CharField(read_only=True)
    original_name = serializers.CharField(write_only=True)
    mime_type = serializers.CharField(write_only=True)

    class Meta:
        model = FileUpload
        fields = (
            "id",
            "file_type",
            "file_category",
            "name",
            "associating_id",
            "signed_url",
            "internal_name",
            "original_name",
            "mime_type",
        )
        write_only_fields = ("associating_id",)

    def create(self, validated_data):
        user = self.context["request"].user
        mime_type = validated_data.pop("mime_type")

        if mime_type not in settings.ALLOWED_MIME_TYPES:
            raise ValidationError({"detail": "Invalid File Type"})

        internal_id = check_permissions(
            validated_data["file_type"], validated_data["associating_id"], user
        )
        associating_id = validated_data["associating_id"]
        validated_data["associating_id"] = internal_id
        validated_data["uploaded_by"] = user
        validated_data["internal_name"] = validated_data["original_name"]
        del validated_data["original_name"]
        file_upload: FileUpload = super().create(validated_data)
        file_upload.signed_url = file_upload.signed_url(mime_type=mime_type)
        if validated_data["file_type"] == FileUpload.FileType.CONSULTATION.value:
            consultation = PatientConsultation.objects.get(external_id=associating_id)
            NotificationGenerator(
                event=Notification.Event.CONSULTATION_FILE_UPLOAD_CREATED,
                caused_by=user,
                caused_object=consultation,
                facility=consultation.facility,
                generate_for_facility=True,
            ).generate()
        if validated_data["file_type"] == FileUpload.FileType.PATIENT.value:
            patient = PatientRegistration.objects.get(external_id=associating_id)
            NotificationGenerator(
                event=Notification.Event.PATIENT_FILE_UPLOAD_CREATED,
                caused_by=user,
                caused_object=patient,
                facility=patient.facility,
                generate_for_facility=True,
            ).generate()
        return file_upload


class FileUploadListSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)
    uploaded_by = UserBaseMinimumSerializer(read_only=True)
    archived_by = UserBaseMinimumSerializer(read_only=True)
    extension = serializers.CharField(source="get_extension", read_only=True)

    class Meta:
        model = FileUpload
        fields = (
            "id",
            "name",
            "associating_id",
            "uploaded_by",
            "archived_by",
            "archived_datetime",
            "upload_completed",
            "is_archived",
            "archive_reason",
            "created_date",
            "file_category",
            "extension",
        )
        read_only_fields = ("associating_id", "name", "created_date")


class FileUploadUpdateSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)
    archived_by = UserBaseMinimumSerializer(read_only=True)

    class Meta:
        model = FileUpload
        fields = (
            "id",
            "name",
            "upload_completed",
            "is_archived",
            "archive_reason",
            "archived_by",
            "archived_datetime",
        )

    def update(self, instance, validated_data):
        user = self.context["request"].user
        if instance.is_archived:
            raise serializers.ValidationError(
                {"file": "Operation not permitted when archived."}
            )
        if user.user_type <= User.TYPE_VALUE_MAP["LocalBodyAdmin"]:
            if instance.uploaded_by == user:
                pass
            else:
                raise serializers.ValidationError(
                    {"permission": "Don't have permission to archive"}
                )
        file = super().update(instance, validated_data)
        if file.is_archived:
            file.archived_by = user
            file.archived_datetime = localtime(now())
            file.save()
        return file

    def validate(self, attrs):
        validated = super().validate(attrs)
        if validated.get("is_archived") and not validated.get("archive_reason"):
            msg = "Archive reason must be specified."
            raise ValidationError(msg)
        return validated


class FileUploadRetrieveSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)
    uploaded_by = UserBaseMinimumSerializer(read_only=True)
    read_signed_url = serializers.CharField(read_only=True)
    extension = serializers.CharField(source="get_extension", read_only=True)

    class Meta:
        model = FileUpload
        fields = (
            "id",
            "name",
            "uploaded_by",
            "upload_completed",
            "is_archived",
            "archive_reason",
            "created_date",
            "read_signed_url",
            "file_category",
            "extension",
        )
        read_only_fields = ("associating_id", "name", "created_date")
