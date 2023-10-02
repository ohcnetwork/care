from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from care.abdm.models import AbhaNumber
from care.abdm.models.base import (
    AccessMode,
    FrequencyUnit,
    HealthInformationTypes,
    Purpose,
    Status,
)
from care.abdm.models.json_schema import CARE_CONTEXTS
from care.abdm.utils.cipher import Cipher
from care.facility.models.file_upload import FileUpload
from care.users.models import User
from care.utils.models.base import BaseModel
from care.utils.models.validators import JSONFieldSchemaValidator


class Consent(BaseModel):
    class Meta:
        abstract = True

    def default_expiry():
        return timezone.now() + timezone.timedelta(days=30)

    def default_from_time():
        return timezone.now() - timezone.timedelta(days=30)

    def default_to_time():
        return timezone.now()

    consent_id = models.UUIDField(null=True, blank=True, unique=True)

    patient_abha = models.ForeignKey(
        AbhaNumber, on_delete=models.PROTECT, to_field="health_id"
    )

    care_contexts = models.JSONField(
        default=list, validators=[JSONFieldSchemaValidator(CARE_CONTEXTS)]
    )

    purpose = models.CharField(
        choices=Purpose.choices, max_length=20, default=Purpose.CARE_MANAGEMENT.value
    )
    hi_types = ArrayField(
        models.CharField(choices=HealthInformationTypes.choices, max_length=20),
        default=list,
    )

    hip = models.CharField(max_length=50, null=True, blank=True)
    hiu = models.CharField(max_length=50, null=True, blank=True)

    requester = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )

    access_mode = models.CharField(
        choices=AccessMode.choices, max_length=20, default=AccessMode.VIEW.value
    )
    from_time = models.DateTimeField(null=True, blank=True, default=default_from_time)
    to_time = models.DateTimeField(null=True, blank=True, default=default_to_time)
    expiry = models.DateTimeField(null=True, blank=True, default=default_expiry)

    frequency_unit = models.CharField(
        choices=FrequencyUnit.choices, max_length=20, default=FrequencyUnit.HOUR.value
    )
    frequency_value = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1)]
    )
    frequency_repeats = models.PositiveSmallIntegerField(default=0)

    def consent_details_dict(self):
        return {
            "patient_abha": self.patient_abha,
            "care_contexts": self.care_contexts,
            "purpose": self.purpose,
            "hi_types": self.hi_types,
            "hip": self.hip,
            "hiu": self.hiu,
            "requester": self.requester,
            "access_mode": self.access_mode,
            "from_time": self.from_time,
            "to_time": self.to_time,
            "expiry": self.expiry,
            "frequency_unit": self.frequency_unit,
            "frequency_value": self.frequency_value,
            "frequency_repeats": self.frequency_repeats,
        }


class ConsentRequest(Consent):
    @property
    def request_id(self):
        return self.consent_id


class ConsentArtefact(Consent):
    @property
    def artefact_id(self):
        return self.external_id

    @property
    def transaction_id(self):
        return self.consent_id

    def save(self, *args, **kwargs):
        if self.key_material_private_key is None:
            cipher = Cipher("", "")
            key_material = cipher.generate_key_pair()

            self.key_material_algorithm = "ECDH"
            self.key_material_curve = "Curve25519"
            self.key_material_public_key = key_material["publicKey"]
            self.key_material_private_key = key_material["privateKey"]
            self.key_material_nonce = key_material["nonce"]

        if self.status in [Status.REVOKED.value, Status.EXPIRED.value]:
            file = FileUpload.objects.filter(
                internal_name=f"{self.external_id}.json",
                file_type=FileUpload.FileType.ABDM_HEALTH_INFORMATION.value,
            ).first()

            if file:
                file.is_archived = True
                file.archived_datetime = timezone.now()
                file.archive_reason = self.status
                file.save()

        return super().save(*args, **kwargs)

    consent_request = models.ForeignKey(
        ConsentRequest,
        on_delete=models.PROTECT,
        to_field="consent_id",
        null=True,
        blank=True,
        related_name="consent_artefacts",
    )

    status = models.CharField(
        choices=Status.choices, max_length=20, default=Status.REQUESTED.value
    )

    cm = models.CharField(max_length=50, null=True, blank=True)

    key_material_algorithm = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        default="ECDH",
    )
    key_material_curve = models.CharField(
        max_length=20, null=True, blank=True, default="Curve25519"
    )
    key_material_public_key = models.CharField(max_length=100, null=True, blank=True)
    key_material_private_key = models.CharField(max_length=200, null=True, blank=True)
    key_material_nonce = models.CharField(max_length=100, null=True, blank=True)

    signature = models.TextField(null=True, blank=True)
