"""
This signal is used to create a patient identifier with the same name as the patient
This allows workflows without strict Authz to function as needed
"""

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from care.emr.models.patient import Patient
from care.emr.signals.patient.base import BasePatientIdentifierConfig


class NameIdentifierConfig(BasePatientIdentifierConfig):
    IDENTIFIER_SYSTEM = "system.care.ohc.network/patient-name"
    CACHED_CONFIG = {}
    DISPLAY = "Patient Name"
    RETRIEVE_WITH_YOB = False
    PARTIAL_SEARCH = True

    @classmethod
    def get_value(cls, patient):
        return patient.name


@receiver(post_save, sender=Patient)
def update_name_identifier(sender, instance, created, **kwargs):
    if settings.MAINTAIN_PATIENT_NAME_IDENTIFIER:
        NameIdentifierConfig.update_identifier(instance)
